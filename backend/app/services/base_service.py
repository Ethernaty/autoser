from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.exceptions import CrossTenantDataViolation, TenantScopeError
from app.core.metrics_hooks import MetricsHook, get_metrics_hook
from app.core.policies import read_retry_policy, run_with_retry, run_with_timeout, write_retry_policy
from app.core.runtime_guards import assert_bounded_structure
from app.core.serialization import JsonSerializer, Serializer
from app.core.tenant_scope import get_current_role, get_current_tenant_id, tenant_scope_context
from app.core.tracing import mark_span_error, start_span
from app.core.uow import SqlAlchemyUnitOfWork


T = TypeVar("T")


@dataclass
class _LockEntry:
    lock: asyncio.Lock
    expires_at_monotonic: float


class _SingleflightRegistry:
    """Bounded lock registry with TTL + LRU eviction."""

    def __init__(self, *, max_size: int, ttl_seconds: float):
        self._max_size = max(128, max_size)
        self._ttl_seconds = max(5.0, ttl_seconds)
        self._entries: OrderedDict[str, _LockEntry] = OrderedDict()
        self._guard = asyncio.Lock()

    async def get_lock(self, key: str) -> asyncio.Lock:
        now = time.monotonic()
        async with self._guard:
            self._evict_expired(now)

            entry = self._entries.get(key)
            if entry is None:
                entry = _LockEntry(lock=asyncio.Lock(), expires_at_monotonic=now + self._ttl_seconds)
                self._entries[key] = entry
            else:
                entry.expires_at_monotonic = now + self._ttl_seconds
                self._entries.move_to_end(key)

            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

            assert_bounded_structure(
                name="singleflight_locks",
                size=len(self._entries),
                limit=self._max_size,
            )

            return entry.lock

    def _evict_expired(self, now: float) -> None:
        expired_keys = [key for key, entry in self._entries.items() if entry.expires_at_monotonic <= now]
        for key in expired_keys:
            self._entries.pop(key, None)


class BaseService:
    """Shared service-level infrastructure for application services."""

    _singleflight_registry: _SingleflightRegistry | None = None

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        session_factory: sessionmaker[Session],
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
        metrics_hook: MetricsHook | None = None,
    ) -> None:
        if tenant_id is None:
            raise TenantScopeError(code="tenant_scope_required", message="Service tenant scope is required")

        context_tenant_id = get_current_tenant_id(required=False)
        if context_tenant_id is not None and context_tenant_id != tenant_id:
            raise TenantScopeError(
                code="tenant_scope_mismatch",
                message="Service tenant does not match request tenant scope",
                details={
                    "context_tenant_id": str(context_tenant_id),
                    "service_tenant_id": str(tenant_id),
                },
            )

        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id
        self._session_factory = session_factory
        self._settings = get_settings()

        self.serializer = serializer or JsonSerializer()
        self.cache = cache_backend or get_cache_backend()
        self.metrics = metrics_hook or get_metrics_hook()
        self._logger = logging.getLogger("app.security.tenant_cache_guard")

    @classmethod
    def _get_singleflight_registry(cls) -> _SingleflightRegistry:
        if cls._singleflight_registry is None:
            settings = get_settings()
            cls._singleflight_registry = _SingleflightRegistry(
                max_size=settings.max_singleflight_locks,
                ttl_seconds=120.0,
            )
        return cls._singleflight_registry

    async def execute_read(self, operation: Callable[[Session], T]) -> T:
        """Execute read operation with transient retry and read timeout policy."""

        async def run_once() -> T:
            def run_sync() -> T:
                with SqlAlchemyUnitOfWork(session_factory=self._session_factory) as uow:
                    if uow.session is None:
                        raise RuntimeError("uow_session_missing")
                    return operation(uow.session)

            return await run_in_threadpool(run_sync)

        policy = read_retry_policy()

        async def wrapped() -> T:
            with start_span(
                f"service.read.{self.__class__.__name__}",
                attributes={
                    "tenant.id": str(self.tenant_id),
                    "service.class": self.__class__.__name__,
                },
            ) as span:
                try:
                    if policy.use_timeout:
                        return await run_with_timeout(run_once, timeout_seconds=self._settings.db_timeout_seconds)
                    return await run_once()
                except Exception as exc:
                    mark_span_error(span, exc)
                    raise

        with tenant_scope_context(
            tenant_id=self.tenant_id,
            user_id=self.actor_user_id,
            role=get_current_role(),
        ):
            return await run_with_retry(wrapped, policy=policy)

    async def execute_write(self, operation: Callable[[Session], T], *, idempotent: bool = False) -> T:
        """Execute write operation with strict transaction boundary and safe retry policy."""

        async def run_once() -> T:
            def run_sync() -> T:
                with SqlAlchemyUnitOfWork(session_factory=self._session_factory) as uow:
                    if uow.session is None:
                        raise RuntimeError("uow_session_missing")
                    return operation(uow.session)

            return await run_in_threadpool(run_sync)

        with tenant_scope_context(
            tenant_id=self.tenant_id,
            user_id=self.actor_user_id,
            role=get_current_role(),
        ):
            with start_span(
                f"service.write.{self.__class__.__name__}",
                attributes={
                    "tenant.id": str(self.tenant_id),
                    "service.class": self.__class__.__name__,
                    "service.idempotent_write": bool(idempotent),
                },
            ) as span:
                try:
                    return await run_with_retry(run_once, policy=write_retry_policy(idempotent=idempotent))
                except Exception as exc:
                    mark_span_error(span, exc)
                    raise

    @classmethod
    async def get_singleflight_lock(cls, key: str) -> asyncio.Lock:
        return await cls._get_singleflight_registry().get_lock(key)

    async def service_rate_limit(self, *, key: str, limit: int, window_seconds: int) -> None:
        self._assert_tenant_cache_key(key)
        current = await self.cache.increment(key, 1, window_seconds)
        if current > limit:
            from app.core.exceptions import AppError

            raise AppError(
                status_code=429,
                code="service_rate_limit_exceeded",
                message="Service rate limit exceeded",
                details={"limit": limit, "window_seconds": window_seconds},
            )

    def _assert_tenant_cache_key(self, key: str) -> None:
        required_prefix = f"tenant:{self.tenant_id}:"
        if not key.startswith(required_prefix):
            raise TenantScopeError(
                code="invalid_tenant_cache_key",
                message="Cache key is missing tenant namespace",
                details={"key": key, "required_prefix": required_prefix},
                status_code=500,
            )

    async def enforce_cache_payload_tenant(self, *, key: str, payload: Any) -> Any:
        """Validate cached payload tenant ownership before returning it."""

        def validate(value: Any) -> None:
            if isinstance(value, dict):
                tenant_value = value.get("tenant_id")
                if tenant_value is not None and str(tenant_value) != str(self.tenant_id):
                    raise CrossTenantDataViolation(
                        details={
                            "cache_key": key,
                            "expected_tenant_id": str(self.tenant_id),
                            "actual_tenant_id": str(tenant_value),
                        }
                    )
                for nested in value.values():
                    validate(nested)
                return

            if isinstance(value, list):
                for nested in value:
                    validate(nested)

        try:
            validate(payload)
        except CrossTenantDataViolation as exc:
            try:
                await self.cache.delete(key)
            except Exception:
                pass
            self._logger.warning(
                "cross_tenant_cache_violation",
                extra={
                    "tenant_id": str(self.tenant_id),
                    "cache_key": key,
                    "details": exc.details,
                },
            )
            raise

        return payload

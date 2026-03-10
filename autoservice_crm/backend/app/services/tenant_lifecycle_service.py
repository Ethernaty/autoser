from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.serialization import JsonSerializer, Serializer
from app.models.tenant import Tenant, TenantState
from app.repositories.tenant_repository import TenantRepository


@dataclass(frozen=True)
class TenantLifecycleInfo:
    tenant_id: UUID
    state: TenantState


class TenantLifecycleService:
    """Tenant lifecycle manager and tenant-state access checks."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        cache_backend: CacheBackend | None = None,
        serializer: Serializer | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._cache = cache_backend or get_cache_backend()
        self._serializer = serializer or JsonSerializer()
        self._cache_ttl = get_settings().tenant_state_cache_ttl_seconds

    async def assert_tenant_active(self, *, tenant_id: UUID) -> None:
        state = await self.get_tenant_state(tenant_id=tenant_id)
        if state != TenantState.ACTIVE:
            raise AppError(
                status_code=403,
                code="tenant_inactive",
                message="Tenant access is restricted",
                details={"tenant_state": state.value},
            )

    async def get_tenant_state(self, *, tenant_id: UUID) -> TenantState:
        key = self._cache_key(tenant_id)
        try:
            cached = await self._cache.get(key)
            if isinstance(cached, str):
                decoded = self._serializer.loads(cached)
                if isinstance(decoded, dict) and "state" in decoded:
                    return TenantState(str(decoded["state"]))
            if isinstance(cached, dict) and "state" in cached:
                return TenantState(str(cached["state"]))
        except Exception:
            pass

        state = await run_in_threadpool(self._fetch_tenant_state, tenant_id)
        payload = {"state": state.value}
        try:
            await self._cache.set(key, self._serializer.dumps(payload), self._cache_ttl)
        except Exception:
            pass
        return state

    async def set_tenant_state(self, *, tenant_id: UUID, state: TenantState) -> TenantLifecycleInfo:
        tenant = await run_in_threadpool(self._set_tenant_state_sync, tenant_id, state)
        await self.invalidate_tenant_state_cache(tenant_id=tenant_id)
        return TenantLifecycleInfo(tenant_id=tenant.id, state=tenant.state)

    async def list_tenants(self, *, limit: int, offset: int) -> list[Tenant]:
        return await run_in_threadpool(self._list_tenants_sync, limit, offset)

    async def get_tenant(self, *, tenant_id: UUID) -> Tenant:
        return await run_in_threadpool(self._get_tenant_sync, tenant_id)

    async def invalidate_tenant_state_cache(self, *, tenant_id: UUID) -> None:
        try:
            await self._cache.delete(self._cache_key(tenant_id))
        except Exception:
            pass

    def _fetch_tenant_state(self, tenant_id: UUID) -> TenantState:
        with self._session_factory() as session:
            with session.begin():
                repo = TenantRepository(session)
                tenant = repo.get_by_id(tenant_id)
                if tenant is None:
                    raise AppError(status_code=404, code="tenant_not_found", message="Tenant not found")
                return tenant.state

    def _set_tenant_state_sync(self, tenant_id: UUID, state: TenantState) -> Tenant:
        with self._session_factory() as session:
            transaction = session.begin()
            try:
                repo = TenantRepository(session)
                tenant = repo.set_state(tenant_id=tenant_id, state=state)
                if tenant is None:
                    raise AppError(status_code=404, code="tenant_not_found", message="Tenant not found")
                transaction.commit()
                return tenant
            except Exception:
                transaction.rollback()
                raise

    def _list_tenants_sync(self, limit: int, offset: int) -> list[Tenant]:
        with self._session_factory() as session:
            with session.begin():
                repo = TenantRepository(session)
                return repo.list_paginated(limit=limit, offset=offset)

    def _get_tenant_sync(self, tenant_id: UUID) -> Tenant:
        with self._session_factory() as session:
            with session.begin():
                repo = TenantRepository(session)
                tenant = repo.get_by_id(tenant_id)
                if tenant is None:
                    raise AppError(status_code=404, code="tenant_not_found", message="Tenant not found")
                return tenant

    @staticmethod
    def _cache_key(tenant_id: UUID) -> str:
        return f"tenant:{tenant_id}:lifecycle:state"

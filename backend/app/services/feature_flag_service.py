from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import CrossTenantDataViolation
from app.core.serialization import JsonSerializer, Serializer
from app.models.subscription import SubscriptionStatus
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.tenant_feature_override_repository import TenantFeatureOverrideRepository
from app.services.base_service import BaseService


@dataclass(frozen=True)
class FeatureResolution:
    enabled: bool
    source: str


class FeatureFlagService(BaseService):
    """Resolve and manage tenant feature flags."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self._cache_ttl = get_settings().billing_cache_ttl_seconds
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )

    async def has_feature(self, *, feature_name: str, default: bool = False) -> bool:
        result = await self.resolve_feature(feature_name=feature_name, default=default)
        return result.enabled

    async def resolve_feature(self, *, feature_name: str, default: bool = False) -> FeatureResolution:
        normalized = feature_name.strip().lower()
        if not normalized:
            return FeatureResolution(enabled=default, source="default")

        namespace = await self._get_namespace_version()
        key = self._feature_key(feature_name=normalized, namespace=namespace)
        cached = await self._safe_get_cached_resolution(key)
        if cached is not None:
            return cached

        def read_op(db: Session) -> dict[str, Any]:
            override_repo = TenantFeatureOverrideRepository(db=db, tenant_id=self.tenant_id)
            override = override_repo.get_by_feature_name(normalized)
            if override is not None:
                return {"enabled": bool(override.enabled), "source": "tenant_override"}

            subscription_repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            subscription = subscription_repo.get_current()
            if subscription is None or subscription.status in {SubscriptionStatus.CANCELED, SubscriptionStatus.SUSPENDED}:
                return {"enabled": default, "source": "default"}

            plan_repo = PlanRepository(db)
            plan = plan_repo.get_by_id(subscription.plan_id)
            if plan is None:
                return {"enabled": default, "source": "default"}

            feature_value = (plan.features_json or {}).get(normalized, default)
            return {"enabled": bool(feature_value), "source": "plan"}

        payload = await self.execute_read(read_op)
        await self._safe_cache_set(key=key, payload=payload)
        return FeatureResolution(enabled=bool(payload.get("enabled", False)), source=str(payload.get("source", "default")))

    async def set_tenant_override(self, *, feature_name: str, enabled: bool) -> None:
        normalized = feature_name.strip().lower()
        if not normalized:
            return

        def write_op(db: Session) -> None:
            repo = TenantFeatureOverrideRepository(db=db, tenant_id=self.tenant_id)
            repo.upsert(feature_name=normalized, enabled=enabled)

        await self.execute_write(write_op, idempotent=True)
        await self._bump_namespace_version()

    async def remove_tenant_override(self, *, feature_name: str) -> None:
        normalized = feature_name.strip().lower()
        if not normalized:
            return

        def write_op(db: Session) -> None:
            repo = TenantFeatureOverrideRepository(db=db, tenant_id=self.tenant_id)
            repo.delete_by_feature_name(normalized)

        await self.execute_write(write_op, idempotent=True)
        await self._bump_namespace_version()

    async def invalidate_feature_cache(self) -> None:
        await self._bump_namespace_version()

    async def _safe_get_cached_resolution(self, key: str) -> FeatureResolution | None:
        self._assert_tenant_cache_key(key)
        try:
            raw = await self.cache.get(key)
            if raw is None:
                return None
            value = self.serializer.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(value, dict):
                return None
            payload = await self.enforce_cache_payload_tenant(
                key=key,
                payload={"tenant_id": self.tenant_id, "payload": value},
            )
            resolved = payload.get("payload", {})
            return FeatureResolution(
                enabled=bool(resolved.get("enabled", False)),
                source=str(resolved.get("source", "cache")),
            )
        except CrossTenantDataViolation:
            raise
        except Exception:
            return None

    async def _safe_cache_set(self, *, key: str, payload: dict[str, Any]) -> None:
        self._assert_tenant_cache_key(key)
        try:
            serialized = self.serializer.dumps({"tenant_id": self.tenant_id, "payload": payload})
            await self.cache.set(key, serialized, self._cache_ttl)
        except Exception:
            return

    async def _get_namespace_version(self) -> int:
        key = self._namespace_key()
        self._assert_tenant_cache_key(key)
        try:
            current = await self.cache.get(key)
            if current is None:
                await self.cache.set_if_absent(key, 1, 60 * 60 * 24 * 30)
                return 1
            return int(current)
        except Exception:
            return 1

    async def _bump_namespace_version(self) -> None:
        key = self._namespace_key()
        self._assert_tenant_cache_key(key)
        try:
            await self.cache.increment(key, 1, 60 * 60 * 24 * 30)
        except Exception:
            return

    def _namespace_key(self) -> str:
        return f"tenant:{self.tenant_id}:billing:feature:namespace"

    def _feature_key(self, *, feature_name: str, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:billing:feature:v{namespace}:{feature_name}"


async def has_feature(*, tenant_id: UUID, feature_name: str) -> bool:
    """Convenience function for tenant feature checks."""
    service = FeatureFlagService(tenant_id=tenant_id)
    return await service.has_feature(feature_name=feature_name, default=False)

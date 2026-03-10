from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.serialization import JsonSerializer, Serializer
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.usage_counter_repository import UsageCounterRepository
from app.services.base_service import BaseService
from app.services.plan_service import PlanService


@dataclass(frozen=True)
class UsageTrackResult:
    tenant_id: UUID
    resource: str
    period_start: date
    used: int
    hard_limit: int
    remaining: int
    soft_warning: bool


class UsageQuotaService(BaseService):
    """Tenant quota tracker with Redis primary and DB fallback storage."""

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
        self._settings = get_settings()
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )

    async def track_usage(self, *, resource: str, amount: int = 1) -> UsageTrackResult:
        normalized_resource = self._normalize_resource(resource)
        if amount <= 0:
            raise AppError(status_code=400, code="invalid_usage_amount", message="Usage amount must be positive")

        period_start = self._current_period_start()
        hard_limit, burst_limit, warning_ratio = await self._resolve_limits(resource=normalized_resource)
        if amount > burst_limit:
            raise AppError(
                status_code=429,
                code="quota_burst_exceeded",
                message="Usage burst limit exceeded",
                details={"burst_limit": burst_limit},
            )

        used = await self._increment_usage_with_fallback(
            resource=normalized_resource,
            period_start=period_start,
            amount=amount,
        )
        if used > hard_limit:
            raise AppError(
                status_code=self._settings.quota_exceeded_status_code,
                code="quota_exceeded",
                message="Resource quota exceeded",
                details={
                    "resource": normalized_resource,
                    "used": used,
                    "limit": hard_limit,
                },
            )

        threshold = int(hard_limit * warning_ratio)
        warning = used >= max(1, threshold)
        if warning:
            await self._mark_soft_warning(resource=normalized_resource, period_start=period_start)

        return UsageTrackResult(
            tenant_id=self.tenant_id,
            resource=normalized_resource,
            period_start=period_start,
            used=used,
            hard_limit=hard_limit,
            remaining=max(0, hard_limit - used),
            soft_warning=warning,
        )

    async def get_usage(self, *, resource: str) -> UsageTrackResult:
        normalized_resource = self._normalize_resource(resource)
        period_start = self._current_period_start()
        hard_limit, _, warning_ratio = await self._resolve_limits(resource=normalized_resource)

        cache_value = await self._try_get_cache_usage(resource=normalized_resource, period_start=period_start)
        if cache_value is not None:
            used = cache_value
        else:
            used = await self._get_usage_from_db(resource=normalized_resource, period_start=period_start)

        threshold = int(hard_limit * warning_ratio)
        warning = used >= max(1, threshold)
        return UsageTrackResult(
            tenant_id=self.tenant_id,
            resource=normalized_resource,
            period_start=period_start,
            used=used,
            hard_limit=hard_limit,
            remaining=max(0, hard_limit - used),
            soft_warning=warning,
        )

    async def _resolve_limits(self, *, resource: str) -> tuple[int, int, float]:
        def read_op(db: Session) -> tuple[int, int, float]:
            subscription_repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            subscription = subscription_repo.get_current()
            if subscription is None:
                return (
                    self._settings.usage_default_hard_limit,
                    self._settings.usage_default_burst_limit,
                    self._settings.usage_warning_ratio,
                )
            plan_repo = PlanRepository(db)
            plan = plan_repo.get_by_id(subscription.plan_id)
            if plan is None:
                return (
                    self._settings.usage_default_hard_limit,
                    self._settings.usage_default_burst_limit,
                    self._settings.usage_warning_ratio,
                )
            hard = PlanService.resolve_limit(plan, resource=resource, default=self._settings.usage_default_hard_limit)
            burst = PlanService.resolve_burst_limit(plan, resource=resource, default=self._settings.usage_default_burst_limit)
            warning_ratio = PlanService.resolve_warning_ratio(
                plan,
                resource=resource,
                default=self._settings.usage_warning_ratio,
            )
            return hard, burst, warning_ratio

        return await self.execute_read(read_op)

    async def _increment_usage_with_fallback(self, *, resource: str, period_start: date, amount: int) -> int:
        key = self._usage_cache_key(resource=resource, period_start=period_start)
        self._assert_tenant_cache_key(key)
        ttl_seconds = max(60, int((self._period_end(period_start) - datetime.now(UTC)).total_seconds()))

        try:
            value = await self.cache.increment(key, amount, ttl_seconds)
            return int(value)
        except Exception:
            return await self._increment_usage_in_db(resource=resource, period_start=period_start, amount=amount)

    async def _increment_usage_in_db(self, *, resource: str, period_start: date, amount: int) -> int:
        def write_op(db: Session) -> int:
            repo = UsageCounterRepository(db=db, tenant_id=self.tenant_id)
            return repo.increment_usage(resource=resource, period_start=period_start, amount=amount)

        return await self.execute_write(write_op, idempotent=False)

    async def _get_usage_from_db(self, *, resource: str, period_start: date) -> int:
        def read_op(db: Session) -> int:
            repo = UsageCounterRepository(db=db, tenant_id=self.tenant_id)
            return repo.current_usage(resource=resource, period_start=period_start)

        return await self.execute_read(read_op)

    async def _mark_soft_warning(self, *, resource: str, period_start: date) -> None:
        def write_op(db: Session) -> None:
            repo = UsageCounterRepository(db=db, tenant_id=self.tenant_id)
            repo.set_soft_warning_sent(resource=resource, period_start=period_start, sent=True)

        try:
            await self.execute_write(write_op, idempotent=True)
        except Exception:
            return

    async def _try_get_cache_usage(self, *, resource: str, period_start: date) -> int | None:
        key = self._usage_cache_key(resource=resource, period_start=period_start)
        self._assert_tenant_cache_key(key)
        try:
            raw = await self.cache.get(key)
            if raw is None:
                return None
            return int(raw)
        except Exception:
            return None

    def _usage_cache_key(self, *, resource: str, period_start: date) -> str:
        return f"tenant:{self.tenant_id}:usage:{resource}:{period_start.strftime('%Y%m')}"

    @staticmethod
    def _normalize_resource(resource: str) -> str:
        normalized = resource.strip().lower()
        if not normalized:
            raise AppError(status_code=400, code="invalid_quota_resource", message="Quota resource is required")
        return normalized

    @staticmethod
    def _current_period_start() -> date:
        now = datetime.now(UTC).date()
        return date(year=now.year, month=now.month, day=1)

    @staticmethod
    def _period_end(period_start: date) -> datetime:
        if period_start.month == 12:
            return datetime(period_start.year + 1, 1, 1, tzinfo=UTC)
        return datetime(period_start.year, period_start.month + 1, 1, tzinfo=UTC)


async def track_usage(*, tenant_id: UUID, resource: str, amount: int = 1) -> UsageTrackResult:
    """Convenience function for quota tracking."""
    service = UsageQuotaService(tenant_id=tenant_id)
    return await service.track_usage(resource=resource, amount=amount)

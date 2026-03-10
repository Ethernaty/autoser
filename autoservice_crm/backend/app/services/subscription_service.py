from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError, CrossTenantDataViolation
from app.core.serialization import JsonSerializer, Serializer
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.billing_event_repository import BillingEventRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.base_service import BaseService
from app.services.feature_flag_service import FeatureFlagService
from app.services.idempotency_service import IdempotencyDecision, IdempotencyService
from app.services.plan_service import PlanService


class SubscriptionService(BaseService):
    """Tenant subscription management with billing-event durability."""

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
        self._cache_ttl = self._settings.billing_cache_ttl_seconds
        self._plan_service = PlanService(session_factory=session_factory or SessionLocal)

        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )
        self._idempotency = IdempotencyService(self)

    async def get_current_subscription(self) -> Subscription:
        namespace = await self._get_namespace_version()
        cache_key = self._subscription_cache_key(namespace=namespace)
        cached = await self._safe_cache_get(cache_key)
        if isinstance(cached, dict):
            return self._payload_to_subscription(cached)

        def read_op(db: Session) -> dict[str, Any]:
            repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            subscription = repo.get_current()
            if subscription is None:
                raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")
            return self._subscription_to_payload(subscription)

        payload = await self.execute_read(read_op)
        await self._safe_cache_set(cache_key, payload)
        return self._payload_to_subscription(payload)

    async def get_effective_plan(self) -> Plan:
        subscription = await self.get_current_subscription()
        return await self._plan_service.get_plan(plan_id=subscription.plan_id)

    async def list_active_plans(self) -> list[Plan]:
        return await self._plan_service.list_active_plans()

    async def change_plan(
        self,
        *,
        plan_id: UUID,
        cancel_at_period_end: bool,
        idempotency_key: str,
    ) -> Subscription:
        self._assert_manageable_role()

        plan = await self._plan_service.get_plan(plan_id=plan_id)
        now = datetime.now(UTC)
        period_end = now + timedelta(days=30)
        payload_hash = self._idempotency.build_request_hash(
            {
                "tenant_id": str(self.tenant_id),
                "plan_id": str(plan.id),
                "cancel_at_period_end": bool(cancel_at_period_end),
            }
        )

        decision = await self._begin_billing_idempotency(
            route="POST:/subscription/change-plan",
            key=idempotency_key,
            request_hash=payload_hash,
        )
        if not decision.proceed:
            if not isinstance(decision.response_payload, dict):
                raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
            return self._payload_to_subscription(decision.response_payload)

        def write_op(db: Session) -> dict[str, Any]:
            subscription_repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            existing = subscription_repo.get_current()
            if existing is None:
                subscription = subscription_repo.create_subscription(
                    plan_id=plan.id,
                    status=SubscriptionStatus.TRIAL if self._settings.default_trial_days > 0 else SubscriptionStatus.ACTIVE,
                    current_period_start=now,
                    current_period_end=period_end,
                    cancel_at_period_end=cancel_at_period_end,
                    trial_end=now + timedelta(days=self._settings.default_trial_days)
                    if self._settings.default_trial_days > 0
                    else None,
                )
                event_type = "subscription.created"
                old_plan_id = None
            else:
                old_plan_id = existing.plan_id
                status = existing.status
                if status in {SubscriptionStatus.CANCELED, SubscriptionStatus.SUSPENDED}:
                    status = SubscriptionStatus.ACTIVE
                subscription = subscription_repo.update_current(
                    plan_id=plan.id,
                    status=status,
                    current_period_start=now,
                    current_period_end=period_end,
                    cancel_at_period_end=cancel_at_period_end,
                )
                if subscription is None:
                    raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")
                event_type = "subscription.plan_changed"

            event_repo = BillingEventRepository(db=db, tenant_id=self.tenant_id)
            event_repo.create_event(
                event_type=event_type,
                payload={
                    "tenant_id": str(self.tenant_id),
                    "old_plan_id": str(old_plan_id) if old_plan_id else None,
                    "new_plan_id": str(plan.id),
                    "cancel_at_period_end": cancel_at_period_end,
                    "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
                    "occurred_at": now.isoformat(),
                },
            )
            return self._subscription_to_payload(subscription)

        try:
            subscription_payload = await self.execute_write(write_op, idempotent=True)
        except Exception:
            await self._safe_mark_failed(decision)
            raise

        await self._mark_succeeded(decision=decision, payload=subscription_payload)
        await self._invalidate_after_mutation()
        return self._payload_to_subscription(subscription_payload)

    async def cancel_subscription(
        self,
        *,
        cancel_at_period_end: bool,
        idempotency_key: str,
    ) -> Subscription:
        self._assert_manageable_role()
        payload_hash = self._idempotency.build_request_hash(
            {
                "tenant_id": str(self.tenant_id),
                "cancel_at_period_end": bool(cancel_at_period_end),
            }
        )
        decision = await self._begin_billing_idempotency(
            route="POST:/subscription/cancel",
            key=idempotency_key,
            request_hash=payload_hash,
        )
        if not decision.proceed:
            if not isinstance(decision.response_payload, dict):
                raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
            return self._payload_to_subscription(decision.response_payload)

        def write_op(db: Session) -> dict[str, Any]:
            repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            subscription = repo.get_current()
            if subscription is None:
                raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")
            next_status = SubscriptionStatus.CANCELED if not cancel_at_period_end else subscription.status
            updated = repo.update_current(
                status=next_status,
                cancel_at_period_end=cancel_at_period_end,
            )
            if updated is None:
                raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")

            event_repo = BillingEventRepository(db=db, tenant_id=self.tenant_id)
            event_repo.create_event(
                event_type="subscription.canceled",
                payload={
                    "tenant_id": str(self.tenant_id),
                    "cancel_at_period_end": cancel_at_period_end,
                    "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
                },
            )
            return self._subscription_to_payload(updated)

        try:
            subscription_payload = await self.execute_write(write_op, idempotent=True)
        except Exception:
            await self._safe_mark_failed(decision)
            raise

        await self._mark_succeeded(decision=decision, payload=subscription_payload)
        await self._invalidate_after_mutation()
        return self._payload_to_subscription(subscription_payload)

    async def set_status(
        self,
        *,
        status: SubscriptionStatus,
        idempotency_key: str,
        event_type: str = "subscription.status_changed",
    ) -> Subscription:
        payload_hash = self._idempotency.build_request_hash(
            {
                "tenant_id": str(self.tenant_id),
                "status": status.value,
            }
        )
        decision = await self._begin_billing_idempotency(
            route="POST:/subscription/status",
            key=idempotency_key,
            request_hash=payload_hash,
        )
        if not decision.proceed:
            if not isinstance(decision.response_payload, dict):
                raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
            return self._payload_to_subscription(decision.response_payload)

        def write_op(db: Session) -> dict[str, Any]:
            repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            subscription = repo.get_current()
            if subscription is None:
                raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")
            updated = repo.update_current(status=status)
            if updated is None:
                raise AppError(status_code=404, code="subscription_not_found", message="Subscription not found")

            event_repo = BillingEventRepository(db=db, tenant_id=self.tenant_id)
            event_repo.create_event(
                event_type=event_type,
                payload={
                    "tenant_id": str(self.tenant_id),
                    "status": status.value,
                    "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
                },
            )
            return self._subscription_to_payload(updated)

        try:
            subscription_payload = await self.execute_write(write_op, idempotent=True)
        except Exception:
            await self._safe_mark_failed(decision)
            raise

        await self._mark_succeeded(decision=decision, payload=subscription_payload)
        await self._invalidate_after_mutation()
        return self._payload_to_subscription(subscription_payload)

    async def list_billing_events(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        def read_op(db: Session) -> list[dict[str, Any]]:
            repo = BillingEventRepository(db=db, tenant_id=self.tenant_id)
            events = repo.list_events(limit=limit, offset=offset)
            return [
                {
                    "id": event.id,
                    "tenant_id": event.tenant_id,
                    "type": event.type,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
                for event in events
            ]

        return await self.execute_read(read_op)

    async def bootstrap_trial_subscription(self) -> Subscription:
        """Create trial subscription if tenant has none."""

        def write_op(db: Session) -> dict[str, Any]:
            subscription_repo = SubscriptionRepository(db=db, tenant_id=self.tenant_id)
            existing = subscription_repo.get_current()
            if existing is not None:
                return self._subscription_to_payload(existing)

            plan_repo = PlanRepository(db)
            plan = plan_repo.get_by_name(self._settings.default_plan_name)
            if plan is None:
                active = plan_repo.list_active()
                if not active:
                    raise AppError(status_code=503, code="plan_not_found", message="No active plans configured")
                plan = active[0]

            now = datetime.now(UTC)
            trial_end = now + timedelta(days=self._settings.default_trial_days) if self._settings.default_trial_days > 0 else None
            subscription = subscription_repo.create_subscription(
                plan_id=plan.id,
                status=SubscriptionStatus.TRIAL if trial_end else SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                cancel_at_period_end=False,
                trial_end=trial_end,
            )
            event_repo = BillingEventRepository(db=db, tenant_id=self.tenant_id)
            event_repo.create_event(
                event_type="subscription.bootstrap",
                payload={
                    "tenant_id": str(self.tenant_id),
                    "plan_id": str(plan.id),
                    "status": subscription.status.value,
                },
            )
            return self._subscription_to_payload(subscription)

        payload = await self.execute_write(write_op, idempotent=True)
        await self._invalidate_after_mutation()
        return self._payload_to_subscription(payload)

    async def _begin_billing_idempotency(self, *, route: str, key: str, request_hash: str) -> IdempotencyDecision:
        normalized = key.strip()
        if not normalized:
            raise AppError(status_code=400, code="idempotency_key_required", message="Idempotency-Key header is required")
        actor_id = self.actor_user_id or self.tenant_id
        return await self._idempotency.begin(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            route=route,
            key=normalized[:128],
            request_hash=request_hash,
        )

    async def _mark_succeeded(self, *, decision: IdempotencyDecision, payload: dict[str, Any]) -> None:
        if decision.record_id is None:
            return
        await self._idempotency.mark_succeeded(tenant_id=self.tenant_id, record_id=decision.record_id, response_payload=payload)

    async def _safe_mark_failed(self, decision: IdempotencyDecision) -> None:
        if decision.record_id is None:
            return
        try:
            await self._idempotency.mark_failed(tenant_id=self.tenant_id, record_id=decision.record_id)
        except Exception:
            return

    async def _invalidate_after_mutation(self) -> None:
        await self._bump_namespace_version()
        feature_service = FeatureFlagService(
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            actor_role=self.actor_role,
            session_factory=self._session_factory,
            cache_backend=self.cache,
            serializer=self.serializer,
        )
        await feature_service.invalidate_feature_cache()

    def _assert_manageable_role(self) -> None:
        if self.actor_role in {"owner", "admin"}:
            return
        raise AppError(status_code=403, code="permission_denied", message="Permission denied")

    async def _safe_cache_get(self, key: str) -> dict[str, Any] | None:
        self._assert_tenant_cache_key(key)
        try:
            raw = await self.cache.get(key)
            if raw is None:
                return None
            value = self.serializer.loads(raw) if isinstance(raw, str) else raw
            guarded = await self.enforce_cache_payload_tenant(
                key=key,
                payload=value,
            )
            return guarded if isinstance(guarded, dict) else None
        except CrossTenantDataViolation:
            raise
        except Exception:
            return None

    async def _safe_cache_set(self, key: str, payload: dict[str, Any]) -> None:
        self._assert_tenant_cache_key(key)
        try:
            await self.cache.set(key, self.serializer.dumps(payload), self._cache_ttl)
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
        return f"tenant:{self.tenant_id}:billing:subscription:namespace"

    def _subscription_cache_key(self, *, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:billing:subscription:v{namespace}:current"

    @staticmethod
    def _subscription_to_payload(subscription: Subscription) -> dict[str, Any]:
        return {
            "id": subscription.id,
            "tenant_id": subscription.tenant_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status.value if isinstance(subscription.status, SubscriptionStatus) else str(subscription.status),
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "trial_end": subscription.trial_end,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
        }

    @staticmethod
    def _payload_to_subscription(payload: dict[str, Any]) -> Subscription:
        def _to_datetime(value: Any) -> datetime | None:
            if value is None or isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value))

        return Subscription(
            id=payload["id"] if isinstance(payload["id"], UUID) else UUID(str(payload["id"])),
            tenant_id=payload["tenant_id"]
            if isinstance(payload["tenant_id"], UUID)
            else UUID(str(payload["tenant_id"])),
            plan_id=payload["plan_id"] if isinstance(payload["plan_id"], UUID) else UUID(str(payload["plan_id"])),
            status=SubscriptionStatus(str(payload["status"])),
            current_period_start=_to_datetime(payload["current_period_start"]) or datetime.now(UTC),
            current_period_end=_to_datetime(payload["current_period_end"]) or datetime.now(UTC),
            cancel_at_period_end=bool(payload.get("cancel_at_period_end", False)),
            trial_end=_to_datetime(payload.get("trial_end")),
            created_at=_to_datetime(payload["created_at"]) or datetime.now(UTC),
            updated_at=_to_datetime(payload["updated_at"]) or datetime.now(UTC),
        )

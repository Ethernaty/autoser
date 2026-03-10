from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID, uuid4

from app.core.exceptions import AppError
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.services.subscription_service import SubscriptionService
from app.services.tenant_lifecycle_service import TenantLifecycleService


DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 50
SEARCH_SCAN_LIMIT = 2_000


@dataclass(frozen=True)
class SubscriptionRowView:
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    plan_name: str
    plan_price: str
    renewal_date: datetime | None
    payment_status: str
    can_cancel: bool


@dataclass(frozen=True)
class SubscriptionListView:
    rows: list[SubscriptionRowView]
    q: str
    page: int
    per_page: int
    has_prev: bool
    has_next: bool
    action_error: str | None = None


class SubscriptionsAdminService:
    """Presentation-facing orchestrator for subscriptions admin pages."""

    def __init__(self, *, tenant_service: TenantLifecycleService | None = None) -> None:
        self._tenant_service = tenant_service or TenantLifecycleService()

    async def build_list_view(
        self,
        *,
        q: str,
        page: int,
        per_page: int,
        action_error: str | None = None,
    ) -> SubscriptionListView:
        normalized_query = q.strip().lower()
        safe_page = max(1, page)
        safe_per_page = max(1, min(per_page, MAX_PER_PAGE))

        tenants, has_next = await self._list_tenants_page(
            q=normalized_query,
            page=safe_page,
            per_page=safe_per_page,
        )
        rows = await self._to_rows(tenants)

        return SubscriptionListView(
            rows=rows,
            q=normalized_query,
            page=safe_page,
            per_page=safe_per_page,
            has_prev=safe_page > 1,
            has_next=has_next,
            action_error=action_error,
        )

    async def cancel_subscription(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
    ) -> None:
        service = SubscriptionService(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
        await service.cancel_subscription(
            cancel_at_period_end=False,
            idempotency_key=uuid4().hex,
        )

    async def _list_tenants_page(
        self,
        *,
        q: str,
        page: int,
        per_page: int,
    ) -> tuple[list[Tenant], bool]:
        if not q:
            offset = (page - 1) * per_page
            chunk = await self._tenant_service.list_tenants(limit=per_page + 1, offset=offset)
            return chunk[:per_page], len(chunk) > per_page

        needed = (page * per_page) + 1
        matched: list[Tenant] = []
        scanned = 0
        offset = 0
        batch_size = max(per_page * 4, 50)

        while len(matched) < needed and scanned < SEARCH_SCAN_LIMIT:
            remaining_scan = SEARCH_SCAN_LIMIT - scanned
            limit = min(batch_size, remaining_scan)
            chunk = await self._tenant_service.list_tenants(limit=limit, offset=offset)
            if not chunk:
                break

            scanned += len(chunk)
            offset += len(chunk)

            for tenant in chunk:
                if self._tenant_matches(tenant=tenant, q=q):
                    matched.append(tenant)
                    if len(matched) >= needed:
                        break

            if len(chunk) < limit:
                break

        start = (page - 1) * per_page
        end = start + per_page
        return matched[start:end], len(matched) > end

    @staticmethod
    def _tenant_matches(*, tenant: Tenant, q: str) -> bool:
        haystack = " ".join(
            [
                str(tenant.id),
                tenant.name,
                tenant.slug,
                tenant.state.value if hasattr(tenant.state, "value") else str(tenant.state),
            ]
        ).lower()
        return q in haystack

    async def _to_rows(self, tenants: Sequence[Tenant]) -> list[SubscriptionRowView]:
        async def to_row(tenant: Tenant) -> SubscriptionRowView:
            subscription_service = SubscriptionService(
                tenant_id=tenant.id,
                actor_user_id=None,
                actor_role="owner",
            )
            try:
                subscription = await subscription_service.get_current_subscription()
                plan = await subscription_service.get_effective_plan()
                plan_name = plan.name
                plan_price = self._format_price(plan.price)
                renewal_date = subscription.current_period_end
                payment_status = self._payment_status(subscription)
                can_cancel = self._can_cancel(subscription)
            except AppError as exc:
                if exc.code in {"subscription_not_found", "plan_not_found"}:
                    plan_name = "n/a"
                    plan_price = "-"
                    renewal_date = None
                    payment_status = "none"
                    can_cancel = False
                else:
                    plan_name = "unavailable"
                    plan_price = "-"
                    renewal_date = None
                    payment_status = "unavailable"
                    can_cancel = False
            except Exception:
                plan_name = "unavailable"
                plan_price = "-"
                renewal_date = None
                payment_status = "unavailable"
                can_cancel = False

            return SubscriptionRowView(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                tenant_slug=tenant.slug,
                plan_name=plan_name,
                plan_price=plan_price,
                renewal_date=renewal_date,
                payment_status=payment_status,
                can_cancel=can_cancel,
            )

        return list(await asyncio.gather(*(to_row(item) for item in tenants)))

    @staticmethod
    def _format_price(value: Decimal) -> str:
        return f"{value:.2f}"

    @staticmethod
    def _payment_status(subscription: Subscription) -> str:
        status_value = subscription.status.value if hasattr(subscription.status, "value") else str(subscription.status)
        if subscription.cancel_at_period_end and status_value not in {"canceled", "suspended"}:
            return "cancel_scheduled"
        return status_value

    @staticmethod
    def _can_cancel(subscription: Subscription) -> bool:
        status_value = subscription.status.value if hasattr(subscription.status, "value") else str(subscription.status)
        return status_value in {"active", "trial", "past_due"} and not subscription.cancel_at_period_end

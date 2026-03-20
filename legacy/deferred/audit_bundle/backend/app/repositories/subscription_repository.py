from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.base import BaseRepositoryTenantScoped


class SubscriptionRepository(BaseRepositoryTenantScoped[Subscription]):
    """Tenant-scoped repository for subscriptions."""

    ALLOWED_UPDATE_FIELDS = {
        "plan_id",
        "status",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "trial_end",
    }

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Subscription, tenant_id=tenant_id)

    def get_current(self) -> Subscription | None:
        stmt = self.scoped_select()
        return self.db.execute(stmt).scalar_one_or_none()

    def create_subscription(
        self,
        *,
        plan_id: UUID,
        status: SubscriptionStatus,
        current_period_start: datetime,
        current_period_end: datetime,
        cancel_at_period_end: bool,
        trial_end: datetime | None,
    ) -> Subscription:
        return self.create(
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            trial_end=trial_end,
        )

    def update_current(self, **updates: Any) -> Subscription | None:
        subscription = self.get_current()
        if subscription is None:
            return None

        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(subscription, field, value)
        self.db.flush()
        return subscription

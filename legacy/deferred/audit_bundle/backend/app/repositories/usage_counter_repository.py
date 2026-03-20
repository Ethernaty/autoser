from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.usage_counter import UsageCounter
from app.repositories.base import BaseRepositoryTenantScoped


class UsageCounterRepository(BaseRepositoryTenantScoped[UsageCounter]):
    """Tenant-scoped repository for usage counters."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=UsageCounter, tenant_id=tenant_id)

    def get_counter(self, *, resource: str, period_start: date) -> UsageCounter | None:
        stmt = self.scoped_select(
            UsageCounter.resource == resource,
            UsageCounter.period_start == period_start,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def increment_usage(self, *, resource: str, period_start: date, amount: int) -> int:
        stmt = (
            insert(UsageCounter)
            .values(
                tenant_id=self.tenant_id,
                resource=resource,
                period_start=period_start,
                used=amount,
                soft_warning_sent=False,
            )
            .on_conflict_do_update(
                index_elements=["tenant_id", "resource", "period_start"],
                set_={"used": UsageCounter.used + amount},
            )
            .returning(UsageCounter.used)
        )
        current = self.db.execute(stmt).scalar_one()
        self.db.flush()
        return int(current)

    def set_soft_warning_sent(self, *, resource: str, period_start: date, sent: bool) -> None:
        counter = self.get_counter(resource=resource, period_start=period_start)
        if counter is None:
            return
        counter.soft_warning_sent = sent
        self.db.flush()

    def current_usage(self, *, resource: str, period_start: date) -> int:
        stmt = select(UsageCounter.used).where(
            UsageCounter.tenant_id == self.tenant_id,
            UsageCounter.resource == resource,
            UsageCounter.period_start == period_start,
        )
        value = self.db.execute(stmt).scalar_one_or_none()
        return int(value or 0)

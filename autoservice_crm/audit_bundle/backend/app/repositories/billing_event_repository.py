from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.billing_event import BillingEvent
from app.repositories.base import BaseRepositoryTenantScoped


class BillingEventRepository(BaseRepositoryTenantScoped[BillingEvent]):
    """Append-only tenant-scoped billing event storage."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=BillingEvent, tenant_id=tenant_id)

    def create_event(self, *, event_type: str, payload: dict[str, Any]) -> BillingEvent:
        return self.create(type=event_type, payload=payload)

    def list_events(self, *, limit: int, offset: int) -> list[BillingEvent]:
        stmt = self.scoped_select().order_by(BillingEvent.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

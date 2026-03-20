from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_line import OrderLine
from app.repositories.base import BaseRepositoryTenantScoped


class OrderLineRepository(BaseRepositoryTenantScoped[OrderLine]):
    """Tenant-scoped data access for work-order lines."""

    ALLOWED_UPDATE_FIELDS = {"line_type", "name", "quantity", "unit_price", "line_total", "position", "comment"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=OrderLine, tenant_id=tenant_id)

    def get_by_id(self, entity_id: UUID) -> OrderLine | None:
        stmt = self.scoped_select(OrderLine.id == entity_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_order(self, *, order_id: UUID) -> list[OrderLine]:
        stmt = self.scoped_select(OrderLine.order_id == order_id).order_by(OrderLine.position.asc(), OrderLine.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())

    def update(self, line_id: UUID, **updates: object) -> OrderLine | None:
        line = self.get_by_id(line_id)
        if line is None:
            return None
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(line, field, value)
        self.db.flush()
        return line

    def delete_for_order(self, *, order_id: UUID) -> None:
        stmt = select(OrderLine).where(OrderLine.tenant_id == self.tenant_id, OrderLine.order_id == order_id)
        for line in self.db.execute(stmt).scalars().all():
            self.db.delete(line)
        self.db.flush()

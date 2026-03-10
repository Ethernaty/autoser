from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.repositories.base import BaseRepositoryTenantScoped


class OrderRepository(BaseRepositoryTenantScoped[Order]):
    """Tenant-scoped data access for work orders."""

    ALLOWED_UPDATE_FIELDS = {"description", "price", "status"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Order, tenant_id=tenant_id)

    def paginate(self, *, limit: int, offset: int) -> list[Order]:
        stmt = self.scoped_select().order_by(Order.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def search(self, *, query: str, limit: int, offset: int) -> list[Order]:
        pattern = f"%{query}%"
        stmt = (
            self.scoped_select(or_(Order.description.ilike(pattern), Order.status.ilike(pattern)))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def update(self, order_id: UUID, **updates: object) -> Order | None:
        order = self.get_by_id(order_id)
        if order is None:
            return None
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(order, field, value)
        self.db.flush()
        return order

    def count(self, *, query: str | None = None) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.tenant_id == self.tenant_id)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(or_(Order.description.ilike(pattern), Order.status.ilike(pattern)))
        return int(self.db.execute(stmt).scalar_one())

    def exists_client(self, *, client_id: UUID) -> bool:
        stmt = select(func.count()).select_from(Order).where(
            Order.tenant_id == self.tenant_id,
            Order.client_id == client_id,
        )
        return int(self.db.execute(stmt).scalar_one()) > 0

    @staticmethod
    def normalize_price(value: float | Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"))

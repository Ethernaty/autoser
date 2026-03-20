from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.repositories.base import BaseRepositoryTenantScoped


class PaymentRepository(BaseRepositoryTenantScoped[Payment]):
    """Tenant-scoped data access for payments."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Payment, tenant_id=tenant_id)

    def list_for_order(self, *, order_id: UUID, include_voided: bool = False) -> list[Payment]:
        criteria: list[object] = [Payment.order_id == order_id]
        if not include_voided:
            criteria.append(Payment.voided_at.is_(None))
        stmt = self.scoped_select(*criteria).order_by(Payment.paid_at.desc(), Payment.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def sum_paid_for_order(self, *, order_id: UUID, include_voided: bool = False) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.tenant_id == self.tenant_id,
            Payment.order_id == order_id,
        )
        if not include_voided:
            stmt = stmt.where(Payment.voided_at.is_(None))
        value = self.db.execute(stmt).scalar_one()
        return Decimal(value or 0).quantize(Decimal("0.01"))

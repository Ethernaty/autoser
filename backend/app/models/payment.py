from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"


class Payment(BaseModel, TenantScopedMixin):
    """Tenant-scoped payment transaction for work orders."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_tenant_order", "tenant_id", "order_id"),
        Index("ix_payments_tenant_paid_at", "tenant_id", "paid_at"),
        Index("ix_payments_tenant_voided", "tenant_id", "voided_at"),
    )

    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(
            PaymentMethod,
            name="payment_method",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PaymentMethod.CASH,
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class OrderLineType(str, Enum):
    LABOR = "labor"
    PART = "part"
    MISC = "misc"


class OrderLine(BaseModel, TenantScopedMixin):
    """Tenant-scoped work-order line item."""

    __tablename__ = "order_lines"
    __table_args__ = (
        Index("ix_order_lines_tenant_order", "tenant_id", "order_id"),
        Index("ix_order_lines_tenant_line_type", "tenant_id", "line_type"),
    )

    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_type: Mapped[OrderLineType] = mapped_column(
        SQLEnum(
            OrderLineType,
            name="order_line_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=OrderLineType.LABOR,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("1.00"), server_default=text("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

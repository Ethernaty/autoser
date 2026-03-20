from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class OrderStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Order(BaseModel, TenantScopedMixin):
    """Tenant-scoped work order entity."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_tenant_client", "tenant_id", "client_id"),
        Index("ix_orders_tenant_vehicle", "tenant_id", "vehicle_id"),
        Index("ix_orders_tenant_assigned_user", "tenant_id", "assigned_user_id"),
        Index("ix_orders_tenant_status", "tenant_id", "status"),
        Index("ix_orders_tenant_created_at", "tenant_id", "created_at"),
    )

    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status", native_enum=False),
        nullable=False,
        default=OrderStatus.NEW,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

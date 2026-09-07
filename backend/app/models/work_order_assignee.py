from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class WorkOrderAssignee(BaseModel, TenantScopedMixin):
    """Tenant-scoped assignment link between work orders and employees."""

    __tablename__ = "work_order_assignees"
    __table_args__ = (
        Index("ix_work_order_assignees_tenant_order", "tenant_id", "order_id"),
        Index("ix_work_order_assignees_tenant_user", "tenant_id", "user_id"),
        UniqueConstraint(
            "tenant_id",
            "order_id",
            "user_id",
            name="uq_work_order_assignees_tenant_order_user",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )


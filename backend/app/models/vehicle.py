from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class Vehicle(BaseModel, TenantScopedMixin):
    """Tenant-scoped vehicle linked to a client."""

    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plate_number", name="uq_vehicles_tenant_plate"),
        Index("ix_vehicles_tenant_client", "tenant_id", "client_id"),
        Index("ix_vehicles_tenant_vin", "tenant_id", "vin"),
    )

    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    make_model: Mapped[str] = mapped_column(String(120), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

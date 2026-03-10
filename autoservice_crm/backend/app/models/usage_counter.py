from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class UsageCounter(BaseModel, TenantScopedMixin):
    """Monthly tenant resource usage counter."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "resource", "period_start", name="uq_usage_tenant_resource_period"),
        Index("ix_usage_counters_resource_period", "resource", "period_start"),
    )

    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    soft_warning_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

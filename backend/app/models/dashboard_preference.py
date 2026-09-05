from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class DashboardPreference(BaseModel, TenantScopedMixin):
    """Tenant+user scoped dashboard preferences."""

    __tablename__ = "dashboard_preferences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_dashboard_preferences_tenant_user"),
        Index("ix_dashboard_preferences_tenant_user", "tenant_id", "user_id"),
        Index("ix_dashboard_preferences_tenant_updated", "tenant_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="operations")
    filters_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    layout_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    baseline_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

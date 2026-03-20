from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class WorkspaceSettings(BaseModel, TenantScopedMixin):
    """Tenant-scoped basic service settings."""

    __tablename__ = "workspace_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_workspace_settings_tenant"),
        Index("ix_workspace_settings_tenant_updated", "tenant_id", "updated_at"),
    )

    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    working_hours_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

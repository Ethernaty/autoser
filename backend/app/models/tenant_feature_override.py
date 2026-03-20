from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class TenantFeatureOverride(BaseModel, TenantScopedMixin):
    """Per-tenant feature flag override."""

    __tablename__ = "tenant_feature_overrides"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_name", name="uq_tenant_feature_override"),
        Index("ix_tenant_feature_overrides_feature_name", "feature_name"),
    )

    feature_name: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

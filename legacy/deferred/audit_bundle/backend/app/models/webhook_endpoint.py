from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class WebhookEndpoint(BaseModel, TenantScopedMixin):
    """Configured outbound webhook endpoint."""

    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_tenant_active", "tenant_id", "is_active"),
        Index("ix_webhook_endpoints_tenant_created", "tenant_id", "created_at"),
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    events: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

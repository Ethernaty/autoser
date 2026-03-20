from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class WebhookEvent(BaseModel, TenantScopedMixin):
    """Event store row for externally dispatched domain events."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_tenant_name", "tenant_id", "event_name"),
        Index("ix_webhook_events_tenant_created", "tenant_id", "created_at"),
    )

    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

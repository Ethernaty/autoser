from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class BillingEvent(BaseModel, TenantScopedMixin):
    """Append-only billing event stream for reconciliation and audit."""

    __tablename__ = "billing_events"
    __table_args__ = (
        Index("ix_billing_events_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_billing_events_type", "type"),
    )

    type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

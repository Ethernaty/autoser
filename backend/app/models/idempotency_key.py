from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class IdempotencyStatus(str, Enum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IdempotencyKey(BaseModel, TenantScopedMixin):
    """Idempotency record for write endpoints."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("tenant_id", "actor_id", "route", "key", name="uq_idempotency_scope_key"),
        Index("ix_idempotency_expires_at", "expires_at"),
        Index("ix_idempotency_scope", "tenant_id", "actor_id", "route"),
    )

    actor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    route: Mapped[str] = mapped_column(String(128), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=IdempotencyStatus.PROCESSING.value)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ApiKey(BaseModel):
    """External API key credential bound to a tenant."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_api_keys_tenant_name"),
        Index("ix_api_keys_tenant_id", "tenant_id"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
        Index("ix_api_keys_tenant_revoked", "tenant_id", "revoked_at"),
        Index("ix_api_keys_tenant_expires", "tenant_id", "expires_at"),
    )

    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(24), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

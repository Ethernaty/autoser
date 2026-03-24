from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class Client(BaseModel, TenantScopedMixin):
    """Tenant-scoped CRM client entity."""

    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="uq_clients_tenant_phone"),
        Index("ix_clients_tenant_name", "tenant_id", "name"),
        Index("ix_clients_tenant_phone", "tenant_id", "phone"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": lambda version: 1 if version is None else version + 1,
    }

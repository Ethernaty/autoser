from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class IdMixin:
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TenantScopedMixin:
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )


class BaseModel(Base, IdMixin, CreatedAtMixin):
    __abstract__ = True

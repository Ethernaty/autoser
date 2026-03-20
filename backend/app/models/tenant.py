from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.membership import Membership


class TenantState(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    DELETED = "deleted"


class Tenant(BaseModel):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    state: Mapped[TenantState] = mapped_column(
        SQLEnum(
            TenantState,
            name="tenant_state",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=TenantState.ACTIVE,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

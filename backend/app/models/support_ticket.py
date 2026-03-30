from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantScopedMixin


class SupportTicketCategory(str, Enum):
    GENERAL = "general"
    BUG = "bug"
    PAYMENT = "payment"
    DATA = "data"
    ACCESS = "access"
    OTHER = "other"


class SupportTicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(BaseModel, TenantScopedMixin):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_tenant_created", "tenant_id", "created_at"),
        Index("ix_support_tickets_tenant_status", "tenant_id", "status"),
        Index("ix_support_tickets_tenant_reporter", "tenant_id", "reporter_user_id"),
    )

    reporter_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[SupportTicketCategory] = mapped_column(
        SQLEnum(
            SupportTicketCategory,
            name="support_ticket_category",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SupportTicketCategory.GENERAL,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(
        SQLEnum(
            SupportTicketStatus,
            name="support_ticket_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SupportTicketStatus.OPEN,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

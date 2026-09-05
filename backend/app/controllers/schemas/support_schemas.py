from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.support_ticket import SupportTicketCategory, SupportTicketStatus


class SupportTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=160)
    category: SupportTicketCategory = SupportTicketCategory.GENERAL
    message: str = Field(min_length=1, max_length=6000)


class SupportTicketUpdateStatusRequest(BaseModel):
    status: SupportTicketStatus


class SupportTicketMessageCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)


class SupportTicketMessageResponse(BaseModel):
    id: UUID
    author_user_id: UUID
    author_role: str
    message: str
    created_at: datetime


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    reporter_user_id: UUID
    subject: str
    category: SupportTicketCategory
    message: str
    messages: list[SupportTicketMessageResponse] = Field(default_factory=list)
    status: SupportTicketStatus
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]
    total: int
    limit: int
    offset: int

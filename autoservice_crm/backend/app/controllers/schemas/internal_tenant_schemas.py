from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.tenant import TenantState


class InternalTenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    state: TenantState
    created_at: datetime
    updated_at: datetime


class InternalTenantListResponse(BaseModel):
    items: list[InternalTenantResponse]
    limit: int
    offset: int


class InternalTenantStateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class InternalForcePlanRequest(BaseModel):
    plan_id: UUID

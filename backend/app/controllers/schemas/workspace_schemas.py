from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceContextResponse(BaseModel):
    workspace_id: UUID
    workspace_slug: str
    workspace_name: str
    role: str
    user_id: UUID


class WorkspaceSettingsUpdateRequest(BaseModel):
    service_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=8)
    working_hours_note: str | None = Field(default=None, max_length=2000)


class WorkspaceSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    service_name: str
    phone: str
    address: str | None
    timezone: str
    currency: str
    working_hours_note: str | None
    created_at: datetime
    updated_at: datetime

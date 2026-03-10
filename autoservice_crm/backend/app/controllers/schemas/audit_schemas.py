from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventCreateRequest(BaseModel):
    entity: str = Field(min_length=1, max_length=64)
    entity_id: UUID | None = None
    action: str = Field(min_length=1, max_length=64)
    previous_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class AuditRecordResponse(BaseModel):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    entity: str
    entity_id: UUID | None
    action: str
    previous_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    metadata: dict[str, Any]
    timestamp: datetime


class AuditListResponse(BaseModel):
    items: list[AuditRecordResponse]
    limit: int
    offset: int
    has_next: bool

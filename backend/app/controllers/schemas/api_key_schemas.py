from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None


class ApiKeyIssueResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    plain_key: str
    expires_at: datetime | None
    created_at: datetime


class ApiKeyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=20)
    email: EmailStr | None = None
    comment: str | None = Field(default=None, max_length=5000)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    email: EmailStr | None = None
    comment: str | None = Field(default=None, max_length=5000)
    version: int | None = Field(default=None, ge=1)


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    phone: str
    email: str | None
    comment: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    limit: int
    offset: int


class ClientBatchRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)

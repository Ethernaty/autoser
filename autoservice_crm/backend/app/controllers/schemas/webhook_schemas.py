from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookEndpointCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    description: str | None = Field(default=None, max_length=200)
    events: list[str] = Field(min_length=1)


class WebhookEndpointCreateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    url: str
    description: str | None
    events: list[str]
    is_active: bool
    signing_secret: str
    created_at: datetime
    updated_at: datetime


class WebhookEndpointResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    url: str
    description: str | None
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookPublishRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookPublishResponse(BaseModel):
    event_id: UUID


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    endpoint_id: UUID
    event_id: UUID
    status: str
    attempt: int
    max_attempts: int
    response_code: int | None
    response_body: str | None
    error: str | None
    next_retry_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreateRequest(BaseModel):
    client_id: UUID
    plate_number: str = Field(min_length=1, max_length=20)
    make_model: str = Field(min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1900, le=2100)
    vin: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)


class VehicleUpdateRequest(BaseModel):
    plate_number: str | None = Field(default=None, min_length=1, max_length=20)
    make_model: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1900, le=2100)
    vin: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    archived: bool | None = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    client_id: UUID
    plate_number: str
    make_model: str
    year: int | None
    vin: str | None
    comment: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    total: int
    limit: int
    offset: int

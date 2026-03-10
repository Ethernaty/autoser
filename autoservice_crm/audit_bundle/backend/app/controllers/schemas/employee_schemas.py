from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(min_length=4, max_length=20)


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str
    is_active: bool
    version: int
    created_at: datetime

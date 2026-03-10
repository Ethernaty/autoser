from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.order import OrderStatus


class ExternalClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=20)
    email: EmailStr | None = None
    comment: str | None = Field(default=None, max_length=5000)


class ExternalClientResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    phone: str
    email: str | None
    comment: str | None
    version: int


class ExternalOrderCreateRequest(BaseModel):
    client_id: UUID
    description: str = Field(min_length=1, max_length=5000)
    price: Decimal = Field(gt=0)
    status: OrderStatus = OrderStatus.NEW


class ExternalOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    description: str
    price: Decimal
    status: OrderStatus

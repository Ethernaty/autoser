from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    client_id: UUID
    description: str = Field(min_length=1, max_length=5000)
    price: Decimal = Field(gt=0)
    status: OrderStatus = OrderStatus.NEW


class OrderUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    price: Decimal | None = Field(default=None, gt=0)
    status: OrderStatus | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    client_id: UUID
    description: str
    price: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    limit: int
    offset: int

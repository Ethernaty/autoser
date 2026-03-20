from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.order import OrderStatus
from app.models.order_line import OrderLineType
from app.models.payment import PaymentMethod


class WorkOrderCreateRequest(BaseModel):
    client_id: UUID
    vehicle_id: UUID
    description: str = Field(min_length=1, max_length=5000)
    total_amount: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    status: OrderStatus = OrderStatus.NEW
    assigned_employee_id: UUID | None = None
    assigned_user_id: UUID | None = None

    @model_validator(mode="after")
    def validate_amount(self) -> "WorkOrderCreateRequest":
        if self.total_amount is None and self.price is None:
            raise ValueError("total_amount is required")
        return self

    @property
    def effective_total_amount(self) -> Decimal:
        assert self.total_amount is not None or self.price is not None
        return self.total_amount if self.total_amount is not None else self.price  # type: ignore[return-value]

    @property
    def effective_assignee_id(self) -> UUID | None:
        return self.assigned_employee_id or self.assigned_user_id


class WorkOrderUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    total_amount: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    status: OrderStatus | None = None
    vehicle_id: UUID | None = None
    assigned_employee_id: UUID | None = None
    assigned_user_id: UUID | None = None

    @property
    def effective_assignee_id(self) -> UUID | None:
        return self.assigned_employee_id or self.assigned_user_id


class WorkOrderStatusRequest(BaseModel):
    status: OrderStatus


class WorkOrderAssignRequest(BaseModel):
    employee_id: UUID | None = None
    user_id: UUID | None = None

    @property
    def effective_employee_id(self) -> UUID | None:
        return self.employee_id or self.user_id


class WorkOrderAttachVehicleRequest(BaseModel):
    vehicle_id: UUID


class OrderLineCreateRequest(BaseModel):
    line_type: OrderLineType
    name: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    position: int | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)


class OrderLineUpdateRequest(BaseModel):
    line_type: OrderLineType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, gt=0)
    position: int | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)


class OrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    order_id: UUID
    line_type: OrderLineType
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    position: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


class PaymentCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    paid_at: datetime | None = None
    comment: str | None = Field(default=None, max_length=2000)
    external_ref: str | None = Field(default=None, max_length=120)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    order_id: UUID
    created_by_user_id: UUID
    amount: Decimal
    method: PaymentMethod
    paid_at: datetime
    comment: str | None
    external_ref: str | None
    voided_at: datetime | None
    created_at: datetime


class WorkOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    vehicle_id: UUID | None
    assigned_employee_id: UUID | None
    assigned_user_id: UUID | None
    description: str
    total_amount: Decimal
    price: Decimal
    status: OrderStatus
    paid_amount: Decimal
    remaining_amount: Decimal
    created_at: datetime
    updated_at: datetime


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    limit: int
    offset: int

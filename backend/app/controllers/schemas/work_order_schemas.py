from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.models.order_line import OrderLineType
from app.models.payment import PaymentMethod


class IntakeDetails(BaseModel):
    mileage: int | None = Field(default=None, ge=0, le=10000000)
    due_at: AwareDatetime | None = None
    estimated_amount: Decimal | None = Field(default=None, ge=0, le=9999999999)
    diagnosis: str | None = Field(default=None, max_length=5000)
    intake_notes: str | None = Field(default=None, max_length=5000)


class WorkOrderCreateRequest(IntakeDetails):
    client_id: UUID
    vehicle_id: UUID
    description: str = Field(min_length=1, max_length=5000)
    total_amount: Decimal | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    status: OrderStatus = OrderStatus.NEW
    assigned_employee_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_employee_ids: list[UUID] | None = None

    @property
    def effective_total_amount(self) -> Decimal:
        if self.total_amount is not None:
            return self.total_amount
        if self.price is not None:
            return self.price
        return Decimal("0.00")

    @property
    def effective_assignee_id(self) -> UUID | None:
        return self.assigned_employee_id or self.assigned_user_id

    @property
    def effective_assignee_ids(self) -> list[UUID]:
        if self.assigned_employee_ids is not None:
            return self.assigned_employee_ids
        assignee_id = self.effective_assignee_id
        return [assignee_id] if assignee_id is not None else []


class WorkOrderUpdateRequest(IntakeDetails):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    total_amount: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    status: OrderStatus | None = None
    vehicle_id: UUID | None = None
    assigned_employee_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_employee_ids: list[UUID] | None = None

    @property
    def effective_assignee_id(self) -> UUID | None:
        return self.assigned_employee_id or self.assigned_user_id


class WorkOrderStatusRequest(BaseModel):
    status: OrderStatus


class WorkOrderAssignRequest(BaseModel):
    employee_id: UUID | None = None
    user_id: UUID | None = None
    employee_ids: list[UUID] | None = None
    user_ids: list[UUID] | None = None

    @property
    def effective_employee_id(self) -> UUID | None:
        return self.employee_id or self.user_id

    @property
    def effective_employee_ids(self) -> list[UUID]:
        if self.employee_ids is not None:
            return self.employee_ids
        if self.user_ids is not None:
            return self.user_ids
        single = self.effective_employee_id
        return [single] if single is not None else []


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


class WorkOrderResponse(IntakeDetails):
    id: UUID
    order_number: int
    tenant_id: UUID
    client_id: UUID
    client_name: str | None = None
    vehicle_id: UUID | None
    vehicle_plate_number: str | None = None
    vehicle_make_model: str | None = None
    assigned_employee_ids: list[UUID] = Field(default_factory=list)
    assigned_employee_id: UUID | None
    assigned_user_id: UUID | None
    description: str
    total_amount: Decimal
    price: Decimal
    status: OrderStatus
    payment_state: str
    paid_amount: Decimal
    remaining_amount: Decimal
    created_at: datetime
    updated_at: datetime


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    limit: int
    offset: int


class WorkOrderTimelineEventResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    action: str
    message: str
    user_id: UUID
    actor_email: str | None = None
    actor_role: str | None = None
    created_at: datetime


class WorkOrderTimelineCommentRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)


class WorkOrderHistoryItemResponse(BaseModel):
    id: UUID
    order_number: int
    client_id: UUID
    client_name: str | None = None
    vehicle_id: UUID | None
    vehicle_plate_number: str | None = None
    vehicle_make_model: str | None = None
    description: str
    work_summary: str | None = None
    status: OrderStatus
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    visit_at: datetime
    created_at: datetime
    updated_at: datetime

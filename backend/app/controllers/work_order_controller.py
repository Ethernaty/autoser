from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.work_order_schemas import (
    OrderLineCreateRequest,
    OrderLineResponse,
    OrderLineUpdateRequest,
    PaymentCreateRequest,
    PaymentResponse,
    WorkOrderTimelineEventResponse,
    WorkOrderAssignRequest,
    WorkOrderAttachVehicleRequest,
    WorkOrderCreateRequest,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderStatusRequest,
    WorkOrderUpdateRequest,
)
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.work_order_service import WorkOrderService, WorkOrderFinancials


router = APIRouter(prefix="/work-orders", tags=["Work Orders"])
legacy_router = APIRouter(prefix="/orders", tags=["Orders (Deprecated)"])
MAX_LIMIT = get_settings().max_limit


def get_work_order_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkOrderService:
    return WorkOrderService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


def _to_work_order_response(order, financials: WorkOrderFinancials) -> WorkOrderResponse:
    return WorkOrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        client_id=order.client_id,
        vehicle_id=order.vehicle_id,
        assigned_employee_id=order.assigned_user_id,
        assigned_user_id=order.assigned_user_id,
        description=order.description,
        total_amount=order.total_amount,
        price=order.total_amount,
        status=order.status,
        paid_amount=financials.paid_amount,
        remaining_amount=financials.remaining_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _to_timeline_response(log_item) -> WorkOrderTimelineEventResponse:
    metadata = log_item.metadata_json if isinstance(log_item.metadata_json, dict) else {}
    message = metadata.get("message") if isinstance(metadata.get("message"), str) else log_item.action
    return WorkOrderTimelineEventResponse(
        id=log_item.id,
        work_order_id=log_item.entity_id,
        action=log_item.action,
        message=message,
        user_id=log_item.user_id,
        created_at=log_item.created_at,
    )


@router.post("/", response_model=WorkOrderResponse, dependencies=[Depends(RequirePermission("orders", "create"))])
@legacy_router.post(
    "/",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "create"))],
    include_in_schema=False,
)
async def create_work_order(
    payload: WorkOrderCreateRequest,
    _idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    order = await service.create_work_order(
        client_id=payload.client_id,
        vehicle_id=payload.vehicle_id,
        description=payload.description,
        total_amount=payload.effective_total_amount,
        status=payload.status,
        assigned_user_id=payload.effective_assignee_id,
    )
    financials = await service.get_financials(work_order_id=order.id)
    return _to_work_order_response(order, financials)


@router.get("/", response_model=WorkOrderListResponse, dependencies=[Depends(RequirePermission("orders", "read"))])
@legacy_router.get(
    "/",
    response_model=WorkOrderListResponse,
    dependencies=[Depends(RequirePermission("orders", "read"))],
    include_in_schema=False,
)
async def list_work_orders(
    query: str | None = Query(default=None, alias="q"),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderListResponse:
    items, total = await service.list_work_orders(q=query, limit=limit, offset=offset)
    financials_map = await service.get_financials_map(work_order_ids=[item.id for item in items])
    return WorkOrderListResponse(
        items=[
            _to_work_order_response(
                item,
                financials_map.get(
                    item.id,
                    WorkOrderFinancials(
                        total_amount=Decimal(item.total_amount),
                        paid_amount=Decimal("0.00"),
                        remaining_amount=Decimal(item.total_amount),
                    ),
                ),
            )
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse, dependencies=[Depends(RequirePermission("orders", "read"))])
@legacy_router.get(
    "/{work_order_id}",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "read"))],
    include_in_schema=False,
)
async def get_work_order(work_order_id: UUID, service: WorkOrderService = Depends(get_work_order_service)) -> WorkOrderResponse:
    order = await service.get_work_order(work_order_id=work_order_id)
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.patch("/{work_order_id}", response_model=WorkOrderResponse, dependencies=[Depends(RequirePermission("orders", "update"))])
@legacy_router.patch(
    "/{work_order_id}",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "update"))],
    include_in_schema=False,
)
async def update_work_order(
    work_order_id: UUID,
    payload: WorkOrderUpdateRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    order = await service.update_work_order(
        work_order_id=work_order_id,
        description=payload.description,
        total_amount=payload.total_amount if payload.total_amount is not None else payload.price,
        status=payload.status,
        vehicle_id=payload.vehicle_id,
        assigned_user_id=payload.effective_assignee_id,
    )
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.post(
    "/{work_order_id}/status",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "change_status"))],
)
@legacy_router.post(
    "/{work_order_id}/status",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "change_status"))],
    include_in_schema=False,
)
async def set_work_order_status(
    work_order_id: UUID,
    payload: WorkOrderStatusRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    order = await service.set_status(work_order_id=work_order_id, status=payload.status)
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.post(
    "/{work_order_id}/assign",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "assign"))],
)
async def assign_work_order_employee(
    work_order_id: UUID,
    payload: WorkOrderAssignRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    order = await service.assign_employee(work_order_id=work_order_id, assigned_user_id=payload.effective_employee_id)
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.post(
    "/{work_order_id}/attach-vehicle",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "update"))],
)
async def attach_work_order_vehicle(
    work_order_id: UUID,
    payload: WorkOrderAttachVehicleRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    order = await service.attach_vehicle(work_order_id=work_order_id, vehicle_id=payload.vehicle_id)
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.post(
    "/{work_order_id}/close",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "close"))],
)
async def close_work_order(work_order_id: UUID, service: WorkOrderService = Depends(get_work_order_service)) -> WorkOrderResponse:
    order = await service.close_work_order(work_order_id=work_order_id)
    financials = await service.get_financials(work_order_id=work_order_id)
    return _to_work_order_response(order, financials)


@router.delete(
    "/{work_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders", "delete"))],
)
@legacy_router.delete(
    "/{work_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders", "delete"))],
    include_in_schema=False,
)
async def delete_work_order(work_order_id: UUID, service: WorkOrderService = Depends(get_work_order_service)) -> Response:
    await service.delete_work_order(work_order_id=work_order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{work_order_id}/lines", response_model=list[OrderLineResponse], dependencies=[Depends(RequirePermission("orders", "read"))])
async def list_work_order_lines(
    work_order_id: UUID,
    service: WorkOrderService = Depends(get_work_order_service),
) -> list[OrderLineResponse]:
    lines = await service.list_order_lines(work_order_id=work_order_id)
    return [OrderLineResponse.model_validate(item) for item in lines]


@router.post("/{work_order_id}/lines", response_model=OrderLineResponse, dependencies=[Depends(RequirePermission("orders", "update"))])
async def add_work_order_line(
    work_order_id: UUID,
    payload: OrderLineCreateRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> OrderLineResponse:
    line = await service.add_order_line(
        work_order_id=work_order_id,
        line_type=payload.line_type,
        name=payload.name,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        position=payload.position,
        comment=payload.comment,
    )
    return OrderLineResponse.model_validate(line)


@router.patch(
    "/{work_order_id}/lines/{line_id}",
    response_model=OrderLineResponse,
    dependencies=[Depends(RequirePermission("orders", "update"))],
)
async def update_work_order_line(
    work_order_id: UUID,
    line_id: UUID,
    payload: OrderLineUpdateRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> OrderLineResponse:
    line = await service.update_order_line(
        work_order_id=work_order_id,
        line_id=line_id,
        line_type=payload.line_type,
        name=payload.name,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        position=payload.position,
        comment=payload.comment,
    )
    return OrderLineResponse.model_validate(line)


@router.delete(
    "/{work_order_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders", "update"))],
)
async def remove_work_order_line(
    work_order_id: UUID,
    line_id: UUID,
    service: WorkOrderService = Depends(get_work_order_service),
) -> Response:
    await service.remove_order_line(work_order_id=work_order_id, line_id=line_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{work_order_id}/payments", response_model=list[PaymentResponse], dependencies=[Depends(RequirePermission("payments", "read"))])
async def list_work_order_payments(
    work_order_id: UUID,
    service: WorkOrderService = Depends(get_work_order_service),
) -> list[PaymentResponse]:
    items = await service.list_payments(work_order_id=work_order_id)
    return [PaymentResponse.model_validate(item) for item in items]


@router.get(
    "/{work_order_id}/timeline",
    response_model=list[WorkOrderTimelineEventResponse],
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def list_work_order_timeline(
    work_order_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: WorkOrderService = Depends(get_work_order_service),
) -> list[WorkOrderTimelineEventResponse]:
    items = await service.list_work_order_timeline(work_order_id=work_order_id, limit=limit, offset=offset)
    return [_to_timeline_response(item) for item in items]


@router.post("/{work_order_id}/payments", response_model=PaymentResponse, dependencies=[Depends(RequirePermission("payments", "create"))])
async def create_work_order_payment(
    work_order_id: UUID,
    payload: PaymentCreateRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> PaymentResponse:
    payment = await service.create_payment(
        work_order_id=work_order_id,
        amount=payload.amount,
        method=payload.method,
        paid_at=payload.paid_at,
        comment=payload.comment,
        external_ref=payload.external_ref,
    )
    return PaymentResponse.model_validate(payment)

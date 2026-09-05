from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import StreamingResponse

from app.controllers.schemas.work_order_schemas import (
    OrderLineCreateRequest,
    OrderLineResponse,
    OrderLineUpdateRequest,
    PaymentCreateRequest,
    PaymentResponse,
    PaymentVoidRequest,
    WorkOrderTimelineEventResponse,
    WorkOrderTimelineCommentRequest,
    WorkOrderAssignRequest,
    WorkOrderAttachVehicleRequest,
    WorkOrderCreateRequest,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderStatusRequest,
    WorkOrderUpdateRequest,
)
from app.core.exceptions import AppError
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.client_service import ClientService
from app.services.vehicle_service import VehicleService
from app.services.work_order_document_renderer import (
    WorkOrderDocumentLine,
    WorkOrderDocumentPayment,
    WorkOrderDocumentSnapshot,
    render_work_order_docx,
    render_work_order_html,
    render_work_order_pdf,
)
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


def get_client_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> ClientService:
    return ClientService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def get_vehicle_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> VehicleService:
    return VehicleService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def _to_work_order_response(
    order,
    financials: WorkOrderFinancials,
    *,
    client_name: str | None = None,
    vehicle_plate_number: str | None = None,
    vehicle_make_model: str | None = None,
    assigned_employee_ids: list[UUID] | None = None,
) -> WorkOrderResponse:
    if financials.paid_amount <= Decimal("0.00"):
        payment_state = "unpaid"
    elif financials.remaining_amount <= Decimal("0.00"):
        payment_state = "paid"
    else:
        payment_state = "partial"

    effective_assignee_ids = assigned_employee_ids or ([order.assigned_user_id] if order.assigned_user_id is not None else [])
    primary_assignee_id = effective_assignee_ids[0] if effective_assignee_ids else order.assigned_user_id

    return WorkOrderResponse(
        id=order.id,
        order_number=order.order_number,
        tenant_id=order.tenant_id,
        client_id=order.client_id,
        client_name=client_name,
        vehicle_id=order.vehicle_id,
        vehicle_plate_number=vehicle_plate_number,
        vehicle_make_model=vehicle_make_model,
        assigned_employee_ids=effective_assignee_ids,
        assigned_employee_id=primary_assignee_id,
        assigned_user_id=primary_assignee_id,
        description=order.description,
        mileage=order.mileage,
        due_at=order.due_at,
        estimated_amount=order.estimated_amount,
        diagnosis=order.diagnosis,
        intake_notes=order.intake_notes,
        total_amount=order.total_amount,
        price=order.total_amount,
        status=order.status,
        payment_state=payment_state,
        paid_amount=financials.paid_amount,
        remaining_amount=financials.remaining_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


async def _build_order_party_maps(
    *,
    orders: list,
    client_service: ClientService,
    vehicle_service: VehicleService,
) -> tuple[dict[UUID, str], dict[UUID, object]]:
    client_ids = list({item.client_id for item in orders})
    vehicle_ids = list({item.vehicle_id for item in orders if item.vehicle_id is not None})

    clients = await client_service.list_clients_by_ids(ids=client_ids) if client_ids else []
    vehicles = await vehicle_service.list_by_ids(ids=vehicle_ids, include_archived=True) if vehicle_ids else []

    client_map = {item.id: item.name for item in clients}
    vehicle_map = {item.id: item for item in vehicles}
    return client_map, vehicle_map


def _to_timeline_response(log_item) -> WorkOrderTimelineEventResponse:
    return WorkOrderTimelineEventResponse(
        id=log_item.id,
        work_order_id=log_item.work_order_id,
        action=log_item.action,
        message=log_item.message,
        user_id=log_item.user_id,
        actor_email=log_item.actor_email,
        actor_role=log_item.actor_role,
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
    client_service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
) -> WorkOrderResponse:
    order = await service.create_work_order(
        client_id=payload.client_id,
        vehicle_id=payload.vehicle_id,
        description=payload.description,
        total_amount=payload.effective_total_amount,
        status=payload.status,
        assigned_user_ids=payload.effective_assignee_ids,
        mileage=payload.mileage,
        due_at=payload.due_at,
        estimated_amount=payload.estimated_amount,
        diagnosis=payload.diagnosis,
        intake_notes=payload.intake_notes,
    )
    financials = await service.get_financials(work_order_id=order.id)
    assignee_ids = await service.get_assignee_ids(work_order_id=order.id)
    client_map, vehicle_map = await _build_order_party_maps(
        orders=[order],
        client_service=client_service,
        vehicle_service=vehicle_service,
    )
    vehicle = vehicle_map.get(order.vehicle_id) if order.vehicle_id is not None else None
    return _to_work_order_response(
        order,
        financials,
        client_name=client_map.get(order.client_id),
        vehicle_plate_number=getattr(vehicle, "plate_number", None),
        vehicle_make_model=getattr(vehicle, "make_model", None),
        assigned_employee_ids=assignee_ids,
    )


@router.get("/", response_model=WorkOrderListResponse, dependencies=[Depends(RequirePermission("orders", "read"))])
@legacy_router.get(
    "/",
    response_model=WorkOrderListResponse,
    dependencies=[Depends(RequirePermission("orders", "read"))],
    include_in_schema=False,
)
async def list_work_orders(
    query: str | None = Query(default=None, alias="q"),
    status_scope: str = Query(default="all", max_length=32),
    assignee_scope: str = Query(default="all", max_length=64),
    payment_scope: Literal["all", "unpaid", "partial", "paid", "outstanding"] = Query(default="all"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort: Literal["updated_desc", "created_desc", "amount_desc", "amount_asc", "status"] = Query(default="updated_desc"),
    overdue: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: WorkOrderService = Depends(get_work_order_service),
    client_service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
) -> WorkOrderListResponse:
    items, total = await service.list_work_orders(
        q=query,
        status_scope=status_scope,
        assignee_scope=assignee_scope,
        limit=limit,
        offset=offset, payment_scope=payment_scope, date_from=date_from, date_to=date_to, sort=sort, overdue=overdue,
    )
    summary = await service.get_registry_totals(q=query.strip()[:100] if query else None,
        status_scope=status_scope, assignee_scope=assignee_scope, payment_scope=payment_scope,
        date_from=date_from, date_to=date_to, overdue=overdue)
    financials_map = await service.get_financials_map(work_order_ids=[item.id for item in items])
    assignee_ids_map = await service.get_assignee_ids_map(work_order_ids=[item.id for item in items])
    client_map, vehicle_map = await _build_order_party_maps(
        orders=items,
        client_service=client_service,
        vehicle_service=vehicle_service,
    )
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
                client_name=client_map.get(item.client_id),
                vehicle_plate_number=getattr(vehicle_map.get(item.vehicle_id), "plate_number", None)
                if item.vehicle_id is not None
                else None,
                vehicle_make_model=getattr(vehicle_map.get(item.vehicle_id), "make_model", None)
                if item.vehicle_id is not None
                else None,
                assigned_employee_ids=assignee_ids_map.get(item.id, []),
            )
            for item in items
        ],
        summary=summary,
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
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    client_service = ClientService(tenant_id=service.tenant_id, actor_user_id=service.actor_user_id, actor_role=service.actor_role)
    vehicle_service = VehicleService(tenant_id=service.tenant_id, actor_user_id=service.actor_user_id, actor_role=service.actor_role)
    client_map, vehicle_map = await _build_order_party_maps(orders=[order], client_service=client_service, vehicle_service=vehicle_service)
    vehicle = vehicle_map.get(order.vehicle_id) if order.vehicle_id else None
    return _to_work_order_response(
        order,
        financials,
        client_name=client_map.get(order.client_id),
        vehicle_plate_number=getattr(vehicle, "plate_number", None),
        vehicle_make_model=getattr(vehicle, "make_model", None),
        assigned_employee_ids=assignee_ids,
    )


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
        assigned_user_ids=payload.assigned_employee_ids,
        assigned_user_id=payload.effective_assignee_id,
        mileage=payload.mileage,
        due_at=payload.due_at,
        estimated_amount=payload.estimated_amount,
        diagnosis=payload.diagnosis,
        intake_notes=payload.intake_notes,
    )
    financials = await service.get_financials(work_order_id=work_order_id)
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    return _to_work_order_response(order, financials, assigned_employee_ids=assignee_ids)


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
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    return _to_work_order_response(order, financials, assigned_employee_ids=assignee_ids)


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
    order = await service.assign_employees(work_order_id=work_order_id, assigned_user_ids=payload.effective_employee_ids)
    financials = await service.get_financials(work_order_id=work_order_id)
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    return _to_work_order_response(order, financials, assigned_employee_ids=assignee_ids)


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
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    return _to_work_order_response(order, financials, assigned_employee_ids=assignee_ids)


@router.post(
    "/{work_order_id}/close",
    response_model=WorkOrderResponse,
    dependencies=[Depends(RequirePermission("orders", "close"))],
)
async def close_work_order(work_order_id: UUID, service: WorkOrderService = Depends(get_work_order_service)) -> WorkOrderResponse:
    order = await service.close_work_order(work_order_id=work_order_id)
    financials = await service.get_financials(work_order_id=work_order_id)
    assignee_ids = await service.get_assignee_ids(work_order_id=work_order_id)
    return _to_work_order_response(order, financials, assigned_employee_ids=assignee_ids)


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


@router.post(
    "/{work_order_id}/timeline/comments",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders", "update"))],
)
async def add_work_order_timeline_comment(
    work_order_id: UUID,
    payload: WorkOrderTimelineCommentRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> Response:
    await service.add_timeline_comment(work_order_id=work_order_id, comment=payload.comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post(
    "/{work_order_id}/payments/{payment_id}/void",
    response_model=PaymentResponse,
    dependencies=[Depends(RequirePermission("payments", "create"))],
)
async def void_work_order_payment(
    work_order_id: UUID,
    payment_id: UUID,
    payload: PaymentVoidRequest,
    service: WorkOrderService = Depends(get_work_order_service),
) -> PaymentResponse:
    payment = await service.void_payment(work_order_id=work_order_id, payment_id=payment_id, reason=payload.reason)
    return PaymentResponse.model_validate(payment)


@router.get(
    "/{work_order_id}/document",
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def get_work_order_document(
    work_order_id: UUID,
    format: Literal["pdf", "html", "docx"] = Query(default="pdf"),
    locale: str | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
    client_service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
) -> Response:
    resolved_locale = locale or accept_language
    order = await work_order_service.get_work_order(work_order_id=work_order_id)
    financials = await work_order_service.get_financials(work_order_id=work_order_id)
    lines = await work_order_service.list_order_lines(work_order_id=work_order_id)
    payments = await work_order_service.list_payments(work_order_id=work_order_id)
    client = await client_service.get_client(client_id=order.client_id)
    vehicle = await vehicle_service.get_vehicle(vehicle_id=order.vehicle_id) if order.vehicle_id is not None else None

    snapshot = WorkOrderDocumentSnapshot(
        order_number=order.order_number,
        description=order.description,
        total_amount=Decimal(order.total_amount),
        paid_amount=financials.paid_amount,
        remaining_amount=financials.remaining_amount,
        client_name=client.name,
        client_phone=client.phone,
        client_email=client.email,
        vehicle_plate_number=vehicle.plate_number if vehicle is not None else None,
        vehicle_make_model=vehicle.make_model if vehicle is not None else None,
        vehicle_year=vehicle.year if vehicle is not None else None,
        vehicle_vin=vehicle.vin if vehicle is not None else None,
        lines=[
            WorkOrderDocumentLine(
                line_type=item.line_type.value,
                name=item.name,
                quantity=Decimal(item.quantity),
                unit_price=Decimal(item.unit_price),
                line_total=Decimal(item.line_total),
                comment=item.comment,
            )
            for item in lines
        ],
        payments=[
            WorkOrderDocumentPayment(
                amount=Decimal(item.amount),
                method=item.method.value,
                paid_at=item.paid_at,
                comment=item.comment,
            )
            for item in payments
        ],
    )

    file_name_base = f"work-order-{order.order_number}"
    if format == "html":
        content = render_work_order_html(snapshot, locale=resolved_locale)
        return Response(
            content=content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'inline; filename="{file_name_base}.html"'},
        )
    if format == "docx":
        content = render_work_order_docx(snapshot, locale=resolved_locale)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{file_name_base}.docx"'},
        )
    if format == "pdf":
        try:
            content = render_work_order_pdf(snapshot, locale=resolved_locale)
        except RuntimeError as exc:
            raise AppError(
                status_code=503,
                code="pdf_renderer_unavailable",
                message="PDF renderer is unavailable on this server",
            ) from exc
        return StreamingResponse(
            iter([content]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name_base}.pdf"'},
        )

    raise AppError(status_code=400, code="invalid_document_format", message="Unsupported document format")

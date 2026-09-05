from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.controllers.schemas.vehicle_schemas import (
    VehicleCreateRequest,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdateRequest,
)
from app.controllers.schemas.work_order_schemas import WorkOrderResponse
from app.controllers.schemas.work_order_schemas import WorkOrderHistoryItemResponse
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.client_service import ClientService
from app.services.vehicle_service import VehicleService
from app.services.work_order_service import WorkOrderService


router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
MAX_LIMIT = get_settings().max_limit


def get_vehicle_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> VehicleService:
    return VehicleService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


def get_work_order_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkOrderService:
    return WorkOrderService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def get_client_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> ClientService:
    return ClientService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def _order_to_response(order, paid_amount="0.00", remaining_amount=None) -> WorkOrderResponse:
    paid = paid_amount if isinstance(paid_amount, Decimal) else Decimal(str(paid_amount))
    remaining = remaining_amount if remaining_amount is not None else max(order.total_amount - paid, Decimal("0.00"))
    if paid <= Decimal("0.00"):
        payment_state = "unpaid"
    elif remaining <= Decimal("0.00"):
        payment_state = "paid"
    else:
        payment_state = "partial"
    return WorkOrderResponse(
        id=order.id,
        order_number=order.order_number,
        tenant_id=order.tenant_id,
        client_id=order.client_id,
        vehicle_id=order.vehicle_id,
        assigned_employee_id=order.assigned_user_id,
        assigned_user_id=order.assigned_user_id,
        description=order.description,
        total_amount=order.total_amount,
        price=order.total_amount,
        status=order.status,
        payment_state=payment_state,
        paid_amount=paid,
        remaining_amount=remaining,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _to_work_summary(order_lines: list[object]) -> str | None:
    if not order_lines:
        return None
    names = [str(getattr(item, "name", "")).strip() for item in order_lines if str(getattr(item, "name", "")).strip()]
    if not names:
        return None
    preview = names[:3]
    if len(names) > 3:
        preview.append(f"+{len(names) - 3} more")
    return ", ".join(preview)


def _enrich_vehicle_response(
    *,
    vehicle,
    client_name: str | None = None,
    client_phone: str | None = None,
    work_order_count: int = 0,
    active_work_order_count: int = 0,
    last_activity_at=None,
) -> VehicleResponse:
    base = VehicleResponse.model_validate(vehicle)
    return base.model_copy(
        update={
            "client_name": client_name,
            "client_phone": client_phone,
            "work_order_count": work_order_count,
            "active_work_order_count": active_work_order_count,
            "last_activity_at": last_activity_at,
        }
    )


@router.post("/", response_model=VehicleResponse, dependencies=[Depends(RequirePermission("vehicles", "create"))])
async def create_vehicle(
    payload: VehicleCreateRequest,
    service: VehicleService = Depends(get_vehicle_service),
) -> VehicleResponse:
    vehicle = await service.create_vehicle(
        client_id=payload.client_id,
        plate_number=payload.plate_number,
        make_model=payload.make_model,
        year=payload.year,
        vin=payload.vin,
        comment=payload.comment,
    )
    return VehicleResponse.model_validate(vehicle)


@router.get("/", response_model=VehicleListResponse, dependencies=[Depends(RequirePermission("vehicles", "read"))])
async def list_vehicles(
    query: str | None = Query(default=None, alias="q"),
    client_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: VehicleService = Depends(get_vehicle_service),
    client_service: ClientService = Depends(get_client_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> VehicleListResponse:
    items, total = await service.list_vehicles(q=query, client_id=client_id, limit=limit, offset=offset)
    vehicle_ids = [item.id for item in items]
    client_ids = list({item.client_id for item in items})
    clients = await client_service.list_clients_by_ids(ids=client_ids)
    client_map = {item.id: item for item in clients}
    activity_map = await work_order_service.get_vehicle_relation_stats(vehicle_ids=vehicle_ids)

    response_items: list[VehicleResponse] = []
    for item in items:
        owner = client_map.get(item.client_id)
        activity = activity_map.get(item.id)
        response_items.append(
            _enrich_vehicle_response(
                vehicle=item,
                client_name=owner.name if owner is not None else None,
                client_phone=owner.phone if owner is not None else None,
                work_order_count=activity.total_count if activity is not None else 0,
                active_work_order_count=activity.active_count if activity is not None else 0,
                last_activity_at=activity.last_activity_at if activity is not None else None,
            )
        )

    return VehicleListResponse(
        items=response_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/by-client/{client_id}", response_model=list[VehicleResponse], dependencies=[Depends(RequirePermission("vehicles", "read"))])
async def list_vehicles_by_client(client_id: UUID, service: VehicleService = Depends(get_vehicle_service)) -> list[VehicleResponse]:
    items = await service.list_by_client(client_id=client_id)
    return [VehicleResponse.model_validate(item) for item in items]


@router.get("/{vehicle_id}", response_model=VehicleResponse, dependencies=[Depends(RequirePermission("vehicles", "read"))])
async def get_vehicle(
    vehicle_id: UUID,
    service: VehicleService = Depends(get_vehicle_service),
    client_service: ClientService = Depends(get_client_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> VehicleResponse:
    vehicle = await service.get_vehicle(vehicle_id=vehicle_id)
    clients = await client_service.list_clients_by_ids(ids=[vehicle.client_id])
    owner = clients[0] if clients else None
    activity_map = await work_order_service.get_vehicle_relation_stats(vehicle_ids=[vehicle.id])
    activity = activity_map.get(vehicle.id)
    return _enrich_vehicle_response(
        vehicle=vehicle,
        client_name=owner.name if owner is not None else None,
        client_phone=owner.phone if owner is not None else None,
        work_order_count=activity.total_count if activity is not None else 0,
        active_work_order_count=activity.active_count if activity is not None else 0,
        last_activity_at=activity.last_activity_at if activity is not None else None,
    )


@router.patch("/{vehicle_id}", response_model=VehicleResponse, dependencies=[Depends(RequirePermission("vehicles", "update"))])
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdateRequest,
    service: VehicleService = Depends(get_vehicle_service),
) -> VehicleResponse:
    vehicle = await service.update_vehicle(
        vehicle_id=vehicle_id,
        plate_number=payload.plate_number,
        make_model=payload.make_model,
        year=payload.year,
        vin=payload.vin,
        comment=payload.comment,
        archived=payload.archived,
    )
    return VehicleResponse.model_validate(vehicle)


@router.get(
    "/{vehicle_id}/work-orders",
    response_model=list[WorkOrderResponse],
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def vehicle_work_order_history(
    vehicle_id: UUID,
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> list[WorkOrderResponse]:
    orders = await vehicle_service.list_work_order_history(vehicle_id=vehicle_id, limit=limit, offset=offset)
    financials_map = await work_order_service.get_financials_map(work_order_ids=[item.id for item in orders])
    result: list[WorkOrderResponse] = []
    for order in orders:
        financials = financials_map.get(order.id)
        if financials is None:
            result.append(_order_to_response(order))
            continue
        result.append(_order_to_response(order, paid_amount=financials.paid_amount, remaining_amount=financials.remaining_amount))
    return result


@router.get(
    "/{vehicle_id}/history",
    response_model=list[WorkOrderHistoryItemResponse],
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def vehicle_operational_history(
    vehicle_id: UUID,
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
    client_service: ClientService = Depends(get_client_service),
) -> list[WorkOrderHistoryItemResponse]:
    orders = await vehicle_service.list_work_order_history(vehicle_id=vehicle_id, limit=limit, offset=offset)
    order_ids = [item.id for item in orders]
    client_ids = list({item.client_id for item in orders})
    clients = await client_service.list_clients_by_ids(ids=client_ids)
    client_map = {item.id: item for item in clients}
    financials_map = await work_order_service.get_financials_map(work_order_ids=order_ids)
    lines_map = await work_order_service.get_order_lines_map(work_order_ids=order_ids)

    response: list[WorkOrderHistoryItemResponse] = []
    for order in orders:
        financials = financials_map.get(order.id)
        paid_amount = financials.paid_amount if financials is not None else Decimal("0.00")
        remaining_amount = financials.remaining_amount if financials is not None else max(order.total_amount - paid_amount, Decimal("0.00"))
        client = client_map.get(order.client_id)
        response.append(
            WorkOrderHistoryItemResponse(
                id=order.id,
                order_number=order.order_number,
                client_id=order.client_id,
                client_name=client.name if client is not None else None,
                vehicle_id=order.vehicle_id,
                vehicle_plate_number=None,
                vehicle_make_model=None,
                description=order.description,
                work_summary=_to_work_summary(lines_map.get(order.id, [])),
                status=order.status,
                total_amount=order.total_amount,
                paid_amount=paid_amount,
                remaining_amount=remaining_amount,
                visit_at=order.created_at,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
        )

    return response

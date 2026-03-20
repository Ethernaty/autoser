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
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
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


def _order_to_response(order, paid_amount="0.00", remaining_amount=None) -> WorkOrderResponse:
    paid = paid_amount if isinstance(paid_amount, Decimal) else Decimal(str(paid_amount))
    remaining = remaining_amount if remaining_amount is not None else max(order.total_amount - paid, Decimal("0.00"))
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
        paid_amount=paid,
        remaining_amount=remaining,
        created_at=order.created_at,
        updated_at=order.updated_at,
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
) -> VehicleListResponse:
    items, total = await service.list_vehicles(q=query, client_id=client_id, limit=limit, offset=offset)
    return VehicleListResponse(
        items=[VehicleResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/by-client/{client_id}", response_model=list[VehicleResponse], dependencies=[Depends(RequirePermission("vehicles", "read"))])
async def list_vehicles_by_client(client_id: UUID, service: VehicleService = Depends(get_vehicle_service)) -> list[VehicleResponse]:
    items = await service.list_by_client(client_id=client_id)
    return [VehicleResponse.model_validate(item) for item in items]


@router.get("/{vehicle_id}", response_model=VehicleResponse, dependencies=[Depends(RequirePermission("vehicles", "read"))])
async def get_vehicle(vehicle_id: UUID, service: VehicleService = Depends(get_vehicle_service)) -> VehicleResponse:
    vehicle = await service.get_vehicle(vehicle_id=vehicle_id)
    return VehicleResponse.model_validate(vehicle)


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

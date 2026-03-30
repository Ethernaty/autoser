from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.client_schemas import (
    ClientBatchRequest,
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.controllers.schemas.work_order_schemas import WorkOrderHistoryItemResponse
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.client_service import ClientService
from app.services.vehicle_service import VehicleService
from app.services.work_order_service import WorkOrderService


router = APIRouter(prefix="/clients", tags=["Clients"])
MAX_LIMIT = get_settings().max_limit


def get_client_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> ClientService:
    """Provide tenant-scoped client service."""
    return ClientService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def get_vehicle_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> VehicleService:
    return VehicleService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


def get_work_order_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkOrderService:
    return WorkOrderService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


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


@router.post(
    "/",
    response_model=ClientResponse,
    dependencies=[Depends(RequirePermission("clients", "create"))],
)
async def create_client(
    payload: ClientCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    client = await service.create_client(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        source=payload.source,
        comment=payload.comment,
        idempotency_key=idempotency_key,
    )
    return ClientResponse.model_validate(client)


@router.get(
    "/",
    response_model=ClientListResponse,
    dependencies=[Depends(RequirePermission("clients", "read"))],
)
async def list_clients(
    query: str | None = Query(default=None, alias="q"),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ClientService = Depends(get_client_service),
) -> ClientListResponse:
    if query:
        items = await service.search_clients(query=query, limit=limit, offset=offset)
        total = await service.count_clients(query=query)
    else:
        items = await service.list_clients_paginated(limit=limit, offset=offset)
        total = await service.count_clients()

    return ClientListResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/batch",
    response_model=list[ClientResponse],
    dependencies=[Depends(RequirePermission("clients", "read"))],
)
async def list_clients_batch(
    payload: ClientBatchRequest,
    service: ClientService = Depends(get_client_service),
) -> list[ClientResponse]:
    clients = await service.list_clients_by_ids(ids=payload.ids)
    return [ClientResponse.model_validate(item) for item in clients]


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(RequirePermission("clients", "read"))],
)
async def get_client(client_id: UUID, service: ClientService = Depends(get_client_service)) -> ClientResponse:
    client = await service.get_client(client_id=client_id)
    return ClientResponse.model_validate(client)


@router.get(
    "/{client_id}/work-orders",
    response_model=list[WorkOrderHistoryItemResponse],
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def list_client_work_orders(
    client_id: UUID,
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    client_service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> list[WorkOrderHistoryItemResponse]:
    orders = await client_service.list_work_order_history(client_id=client_id, limit=limit, offset=offset)
    order_ids = [item.id for item in orders]
    vehicle_ids = [item.vehicle_id for item in orders if item.vehicle_id is not None]
    vehicles = await vehicle_service.list_by_ids(ids=vehicle_ids, include_archived=True)
    vehicle_map = {item.id: item for item in vehicles}
    financials_map = await work_order_service.get_financials_map(work_order_ids=order_ids)
    lines_map = await work_order_service.get_order_lines_map(work_order_ids=order_ids)

    response: list[WorkOrderHistoryItemResponse] = []
    for order in orders:
        financials = financials_map.get(order.id)
        paid_amount = financials.paid_amount if financials is not None else Decimal("0.00")
        remaining_amount = financials.remaining_amount if financials is not None else max(order.total_amount - paid_amount, Decimal("0.00"))
        vehicle = vehicle_map.get(order.vehicle_id) if order.vehicle_id is not None else None
        response.append(
            WorkOrderHistoryItemResponse(
                id=order.id,
                client_id=order.client_id,
                client_name=None,
                vehicle_id=order.vehicle_id,
                vehicle_plate_number=vehicle.plate_number if vehicle is not None else None,
                vehicle_make_model=vehicle.make_model if vehicle is not None else None,
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


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(RequirePermission("clients", "update"))],
)
async def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    client = await service.update_client(
        client_id=client_id,
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else payload.email,
        source=payload.source,
        comment=payload.comment,
        expected_version=payload.version,
    )
    return ClientResponse.model_validate(client)


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("clients", "delete"))],
)
async def delete_client(client_id: UUID, service: ClientService = Depends(get_client_service)) -> Response:
    await service.delete_client(client_id=client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

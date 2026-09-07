from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.client_schemas import (
    ClientBatchRequest,
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    ClientImportRequest,
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


def _enrich_client_response(
    *,
    client,
    vehicle_count: int = 0,
    work_order_count: int = 0,
    active_work_order_count: int = 0,
    last_activity_at=None,
) -> ClientResponse:
    base = ClientResponse.model_validate(client)
    return base.model_copy(
        update={
            "vehicle_count": vehicle_count,
            "work_order_count": work_order_count,
            "active_work_order_count": active_work_order_count,
            "last_activity_at": last_activity_at,
        }
    )


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
    sort: Literal["recent", "name", "activity"] = "recent",
    activity: Literal["all", "active", "never", "recent", "inactive"] = "all",
    source: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> ClientListResponse:
    items, summary = await service.directory(query=query, sort=sort, activity=activity, source=source, limit=limit, offset=offset)
    total = summary["total"]

    client_ids = [item.id for item in items]
    vehicle_counts = await vehicle_service.count_by_client_ids(client_ids=client_ids)
    activity_map = await work_order_service.get_client_relation_stats(client_ids=client_ids)

    response_items: list[ClientResponse] = []
    for item in items:
        activity = activity_map.get(item.id)
        response_items.append(
            _enrich_client_response(
                client=item,
                vehicle_count=vehicle_counts.get(item.id, 0),
                work_order_count=activity.total_count if activity is not None else 0,
                active_work_order_count=activity.active_count if activity is not None else 0,
                last_activity_at=activity.last_activity_at if activity is not None else None,
            )
        )

    return ClientListResponse(
        items=response_items,
        total=total,
        limit=limit,
        offset=offset,
        summary=summary,
    )


@router.post("/import", dependencies=[Depends(RequirePermission("clients", "create"))])
async def import_clients(payload: ClientImportRequest, service: ClientService = Depends(get_client_service)):
    return await service.import_clients(csv_text=payload.csv_text, commit=payload.commit)


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
async def get_client(
    client_id: UUID,
    service: ClientService = Depends(get_client_service),
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    work_order_service: WorkOrderService = Depends(get_work_order_service),
) -> ClientResponse:
    client = await service.get_client(client_id=client_id)
    vehicle_counts = await vehicle_service.count_by_client_ids(client_ids=[client.id])
    activity_map = await work_order_service.get_client_relation_stats(client_ids=[client.id])
    activity = activity_map.get(client.id)
    financials = await work_order_service.get_client_financials(client_id=client.id)
    return _enrich_client_response(
        client=client,
        vehicle_count=vehicle_counts.get(client.id, 0),
        work_order_count=activity.total_count if activity is not None else 0,
        active_work_order_count=activity.active_count if activity is not None else 0,
        last_activity_at=activity.last_activity_at if activity is not None else None,
    ).model_copy(update=financials)


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
                order_number=order.order_number,
                client_id=order.client_id,
                client_name=None,
                vehicle_id=order.vehicle_id,
                vehicle_plate_number=vehicle.plate_number if vehicle is not None else None,
                vehicle_make_model=vehicle.make_model if vehicle is not None else None,
                description=order.description,
                work_summary=_to_work_summary(lines_map.get(order.id, [])),
                mileage=order.mileage,
                due_at=order.due_at,
                diagnosis=order.diagnosis,
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

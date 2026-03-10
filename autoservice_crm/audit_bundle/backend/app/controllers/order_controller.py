from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.order_schemas import OrderCreate, OrderListResponse, OrderResponse, OrderUpdate
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.feature_quota_guard import RequireQuota
from app.middleware.permission_guard import RequirePermission
from app.services.order_service import OrderService
from app.services.usage_quota_service import UsageQuotaService
from app.models.order import OrderStatus


router = APIRouter(prefix="/orders", tags=["Orders"])
MAX_LIMIT = get_settings().max_limit


def get_order_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> OrderService:
    return OrderService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
        session_factory=SessionLocal,
    )


async def enforce_payment_quota_on_completion(
    order_id: UUID,
    payload: OrderUpdate,
    context: UserRequestContext = Depends(get_current_user_context),
    order_service: OrderService = Depends(get_order_service),
) -> None:
    if payload.status != OrderStatus.COMPLETED:
        return

    current = await order_service.get_order(order_id=order_id)
    if current.status == OrderStatus.COMPLETED:
        return

    quota_service = UsageQuotaService(
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )
    await quota_service.track_usage(resource="payments", amount=1)


@router.post(
    "/",
    response_model=OrderResponse,
    dependencies=[Depends(RequirePermission("work_orders", "create")), Depends(RequireQuota("orders"))],
)
async def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await service.create_order(
        client_id=payload.client_id,
        description=payload.description,
        price=payload.price,
        status=payload.status,
        idempotency_key=idempotency_key,
    )
    return OrderResponse.model_validate(order)


@router.get(
    "/",
    response_model=OrderListResponse,
    dependencies=[Depends(RequirePermission("work_orders", "read"))],
)
async def list_orders(
    query: str | None = Query(default=None, alias="q"),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    if query:
        items = await service.search_orders(query=query, limit=limit, offset=offset)
        total = await service.count_orders(query=query)
    else:
        items = await service.list_orders_paginated(limit=limit, offset=offset)
        total = await service.count_orders()

    return OrderListResponse(
        items=[OrderResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(RequirePermission("work_orders", "read"))],
)
async def get_order(order_id: UUID, service: OrderService = Depends(get_order_service)) -> OrderResponse:
    order = await service.get_order(order_id=order_id)
    return OrderResponse.model_validate(order)


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[
        Depends(RequirePermission("work_orders", "update")),
        Depends(enforce_payment_quota_on_completion),
    ],
)
async def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await service.update_order(
        order_id=order_id,
        description=payload.description,
        price=payload.price,
        status=payload.status,
    )
    return OrderResponse.model_validate(order)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("work_orders", "delete"))],
)
async def delete_order(order_id: UUID, service: OrderService = Depends(get_order_service)) -> Response:
    await service.delete_order(order_id=order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

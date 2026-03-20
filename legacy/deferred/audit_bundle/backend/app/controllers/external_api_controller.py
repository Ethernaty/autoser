from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.controllers.schemas.external_schemas import (
    ExternalClientCreateRequest,
    ExternalClientResponse,
    ExternalOrderCreateRequest,
    ExternalOrderResponse,
)
from app.core.config import get_settings
from app.core.request_context import ExternalAuthContext, get_external_auth_context
from app.middleware.api_key_scope_guard import RequireExternalScope
from app.services.usage_quota_service import UsageQuotaService
from app.services.client_service import ClientService
from app.services.order_service import OrderService


router = APIRouter(prefix="/external/v1", tags=["External API"])
MAX_LIMIT = get_settings().max_limit


def get_external_client_service(
    auth: ExternalAuthContext = Depends(get_external_auth_context),
) -> ClientService:
    return ClientService(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.principal_id,
        actor_role=auth.role,
    )


def get_external_order_service(
    auth: ExternalAuthContext = Depends(get_external_auth_context),
) -> OrderService:
    return OrderService(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.principal_id,
        actor_role=auth.role,
    )


def RequireExternalQuota(resource: str):
    async def _dependency(auth: ExternalAuthContext = Depends(get_external_auth_context)) -> None:
        service = UsageQuotaService(
            tenant_id=auth.tenant_id,
            actor_user_id=auth.principal_id,
            actor_role=auth.role,
        )
        await service.track_usage(resource=resource, amount=1)

    return _dependency


@router.get(
    "/clients",
    response_model=list[ExternalClientResponse],
    dependencies=[Depends(RequireExternalScope("clients", "read"))],
)
async def external_list_clients(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ClientService = Depends(get_external_client_service),
) -> list[ExternalClientResponse]:
    items = (
        await service.search_clients(query=q, limit=limit, offset=offset)
        if q
        else await service.list_clients_paginated(limit=limit, offset=offset)
    )
    return [
        ExternalClientResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            name=item.name,
            phone=item.phone,
            email=item.email,
            comment=item.comment,
            version=item.version,
        )
        for item in items
    ]


@router.post(
    "/clients",
    response_model=ExternalClientResponse,
    dependencies=[Depends(RequireExternalScope("clients", "write"))],
)
async def external_create_client(
    payload: ExternalClientCreateRequest,
    service: ClientService = Depends(get_external_client_service),
) -> ExternalClientResponse:
    entity = await service.create_client(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        comment=payload.comment,
        idempotency_key=None,
    )
    return ExternalClientResponse(
        id=entity.id,
        tenant_id=entity.tenant_id,
        name=entity.name,
        phone=entity.phone,
        email=entity.email,
        comment=entity.comment,
        version=entity.version,
    )


@router.get(
    "/orders",
    response_model=list[ExternalOrderResponse],
    dependencies=[Depends(RequireExternalScope("orders", "read"))],
)
async def external_list_orders(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: OrderService = Depends(get_external_order_service),
) -> list[ExternalOrderResponse]:
    items = (
        await service.search_orders(query=q, limit=limit, offset=offset)
        if q
        else await service.list_orders_paginated(limit=limit, offset=offset)
    )
    return [
        ExternalOrderResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            client_id=item.client_id,
            description=item.description,
            price=item.price,
            status=item.status,
        )
        for item in items
    ]


@router.post(
    "/orders",
    response_model=ExternalOrderResponse,
    dependencies=[Depends(RequireExternalScope("orders", "write")), Depends(RequireExternalQuota("orders"))],
)
async def external_create_order(
    payload: ExternalOrderCreateRequest,
    service: OrderService = Depends(get_external_order_service),
) -> ExternalOrderResponse:
    entity = await service.create_order(
        client_id=payload.client_id,
        description=payload.description,
        price=payload.price,
        status=payload.status,
    )
    return ExternalOrderResponse(
        id=entity.id,
        tenant_id=entity.tenant_id,
        client_id=entity.client_id,
        description=entity.description,
        price=entity.price,
        status=entity.status,
    )

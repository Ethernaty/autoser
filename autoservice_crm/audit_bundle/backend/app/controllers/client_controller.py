from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.client_schemas import (
    ClientBatchRequest,
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.client_service import ClientService


router = APIRouter(prefix="/clients", tags=["Clients"])
MAX_LIMIT = get_settings().max_limit


def get_client_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> ClientService:
    """Provide tenant-scoped client service."""
    return ClientService(tenant_id=tenant_id, actor_user_id=context.user_id, actor_role=context.role)


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

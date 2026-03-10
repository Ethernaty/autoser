from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.schemas.webhook_schemas import (
    WebhookEndpointCreateRequest,
    WebhookEndpointCreateResponse,
    WebhookDeliveryResponse,
    WebhookEndpointResponse,
    WebhookPublishRequest,
    WebhookPublishResponse,
)
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.services.webhook_service import WebhookService


router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def get_webhook_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WebhookService:
    return WebhookService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.post("/endpoints", response_model=WebhookEndpointCreateResponse)
async def create_webhook_endpoint(
    payload: WebhookEndpointCreateRequest,
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookEndpointCreateResponse:
    created = await service.create_endpoint(
        url=payload.url,
        description=payload.description,
        events=payload.events,
    )
    endpoint = created.endpoint
    return WebhookEndpointCreateResponse(
        id=endpoint.id,
        tenant_id=endpoint.tenant_id,
        url=endpoint.url,
        description=endpoint.description,
        events=list(endpoint.events),
        is_active=endpoint.is_active,
        signing_secret=created.signing_secret,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


@router.get("/endpoints", response_model=list[WebhookEndpointResponse])
async def list_webhook_endpoints(service: WebhookService = Depends(get_webhook_service)) -> list[WebhookEndpointResponse]:
    entities = await service.list_endpoints()
    return [
        WebhookEndpointResponse(
            id=entity.id,
            tenant_id=entity.tenant_id,
            url=entity.url,
            description=entity.description,
            events=list(entity.events),
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        for entity in entities
    ]


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_webhook_endpoint(
    endpoint_id: UUID,
    service: WebhookService = Depends(get_webhook_service),
) -> Response:
    await service.deactivate_endpoint(endpoint_id=endpoint_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/publish", response_model=WebhookPublishResponse)
async def publish_webhook_event(
    payload: WebhookPublishRequest,
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookPublishResponse:
    event_id = await service.publish_event(
        event_name=payload.event_name,
        payload=payload.payload,
    )
    return WebhookPublishResponse(event_id=event_id)


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    service: WebhookService = Depends(get_webhook_service),
) -> list[WebhookDeliveryResponse]:
    entities = await service.list_deliveries(limit=limit, offset=offset, status=status_filter)
    return [
        WebhookDeliveryResponse(
            id=entity.id,
            tenant_id=entity.tenant_id,
            endpoint_id=entity.endpoint_id,
            event_id=entity.event_id,
            status=entity.status,
            attempt=entity.attempt,
            max_attempts=entity.max_attempts,
            response_code=entity.response_code,
            response_body=entity.response_body,
            error=entity.error,
            next_retry_at=entity.next_retry_at,
            delivered_at=entity.delivered_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        for entity in entities
    ]

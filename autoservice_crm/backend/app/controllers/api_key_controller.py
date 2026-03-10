from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.controllers.schemas.api_key_schemas import ApiKeyCreateRequest, ApiKeyIssueResponse, ApiKeyResponse
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.services.api_key_service import ApiKeyService


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def get_api_key_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> ApiKeyService:
    return ApiKeyService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.post("/", response_model=ApiKeyIssueResponse)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    service: ApiKeyService = Depends(get_api_key_service),
) -> ApiKeyIssueResponse:
    issued = await service.create_api_key(
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    return ApiKeyIssueResponse(
        id=issued.api_key.id,
        tenant_id=issued.api_key.tenant_id,
        name=issued.api_key.name,
        key_prefix=issued.api_key.key_prefix,
        scopes=list(issued.api_key.scopes),
        plain_key=issued.plain_key,
        expires_at=issued.api_key.expires_at,
        created_at=issued.api_key.created_at,
    )


@router.get("/", response_model=list[ApiKeyResponse])
async def list_api_keys(service: ApiKeyService = Depends(get_api_key_service)) -> list[ApiKeyResponse]:
    entities = await service.list_api_keys()
    return [
        ApiKeyResponse(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            key_prefix=entity.key_prefix,
            scopes=list(entity.scopes),
            last_used_at=entity.last_used_at,
            expires_at=entity.expires_at,
            revoked_at=entity.revoked_at,
            created_at=entity.created_at,
        )
        for entity in entities
    ]


@router.post("/{api_key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: UUID,
    service: ApiKeyService = Depends(get_api_key_service),
) -> Response:
    await service.revoke_api_key(api_key_id=api_key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

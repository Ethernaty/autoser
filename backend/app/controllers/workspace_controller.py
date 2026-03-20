from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.controllers.schemas.workspace_schemas import (
    WorkspaceContextResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdateRequest,
)
from app.core.exceptions import AppError
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.repositories.auth_repository import AuthRepository
from app.core.database import SessionLocal
from app.services.workspace_settings_service import WorkspaceSettingsService


router = APIRouter(prefix="/workspace", tags=["Workspace"])


def get_workspace_settings_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkspaceSettingsService:
    return WorkspaceSettingsService(tenant_id=tenant_id, actor_user_id=context.user_id)


@router.get("/context", response_model=WorkspaceContextResponse)
def workspace_context(
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkspaceContextResponse:
    db = SessionLocal()
    try:
        transaction = db.begin()
        repo = AuthRepository(db)
        tenant = repo.get_tenant_by_id(context.tenant_id)
        if tenant is None:
            raise AppError(status_code=404, code="workspace_not_found", message="Workspace not found")
        transaction.commit()
        return WorkspaceContextResponse(
            workspace_id=tenant.id,
            workspace_slug=tenant.slug,
            workspace_name=tenant.name,
            role=str(context.role),
            user_id=context.user_id,
        )
    except Exception:
        if "transaction" in locals() and transaction.is_active:
            transaction.rollback()
        raise
    finally:
        db.close()


@router.get(
    "/settings",
    response_model=WorkspaceSettingsResponse,
    dependencies=[Depends(RequirePermission("workspace_settings", "read"))],
)
async def get_workspace_settings(
    service: WorkspaceSettingsService = Depends(get_workspace_settings_service),
) -> WorkspaceSettingsResponse:
    settings = await service.get_settings()
    return WorkspaceSettingsResponse.model_validate(settings)


@router.patch(
    "/settings",
    response_model=WorkspaceSettingsResponse,
    dependencies=[Depends(RequirePermission("workspace_settings", "manage"))],
)
async def update_workspace_settings(
    payload: WorkspaceSettingsUpdateRequest,
    service: WorkspaceSettingsService = Depends(get_workspace_settings_service),
) -> WorkspaceSettingsResponse:
    settings = await service.update_settings(
        service_name=payload.service_name,
        phone=payload.phone,
        address=payload.address,
        timezone=payload.timezone,
        currency=payload.currency,
        working_hours_note=payload.working_hours_note,
    )
    return WorkspaceSettingsResponse.model_validate(settings)

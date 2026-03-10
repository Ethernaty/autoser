from __future__ import annotations

from datetime import UTC, datetime
from fastapi import APIRouter, Depends, Query

from app.controllers.schemas.audit_schemas import (
    AuditEventCreateRequest,
    AuditListResponse,
    AuditRecordResponse,
)
from app.core.internal_auth import require_internal_service_auth
from app.core.request_context import UserRequestContext, get_current_user_context
from app.services.audit_log_query_service import AuditLogQueryService
from app.services.audit_log_service import AuditLogService
from app.core.exceptions import AppError


router = APIRouter(prefix="/audit", tags=["Audit"])


def _assert_admin(context: UserRequestContext) -> None:
    if context.role.strip().lower() in {"owner", "admin"}:
        return
    raise AppError(status_code=403, code="permission_denied", message="Permission denied")


@router.get("/", response_model=AuditListResponse)
async def list_audit_logs(
    context: UserRequestContext = Depends(get_current_user_context),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    level: str | None = Query(default=None),
    search: str | None = Query(default=None, alias="q"),
) -> AuditListResponse:
    _assert_admin(context)
    service = AuditLogQueryService(tenant_id=context.tenant_id)
    page = await service.list_latest_logs(
        limit=limit,
        offset=offset,
        level=level,
        search=search,
        errors_only=False,
    )

    return AuditListResponse(
        items=[
            AuditRecordResponse(
                id=item.id,
                user_id=item.user_id,
                workspace_id=context.tenant_id,
                entity=item.entity,
                entity_id=item.entity_id,
                action=item.action,
                previous_value=item.metadata.get("previous_value") if isinstance(item.metadata, dict) else None,
                new_value=item.metadata.get("new_value") if isinstance(item.metadata, dict) else None,
                metadata=item.metadata if isinstance(item.metadata, dict) else {},
                timestamp=item.created_at,
            )
            for item in page.items
        ],
        limit=page.limit,
        offset=page.offset,
        has_next=page.has_next,
    )


@router.post("/events", status_code=201, dependencies=[Depends(require_internal_service_auth)])
async def create_audit_event(
    payload: AuditEventCreateRequest,
    context: UserRequestContext = Depends(get_current_user_context),
) -> dict[str, str]:
    _assert_admin(context)
    service = AuditLogService(tenant_id=context.tenant_id)
    metadata = {
        "previous_value": payload.previous_value,
        "new_value": payload.new_value,
        "timestamp": datetime.now(UTC).isoformat(),
        **(payload.metadata or {}),
    }

    await service.log_action(
        user_id=context.user_id,
        action=payload.action,
        entity=payload.entity,
        entity_id=payload.entity_id,
        metadata=metadata,
    )

    return {"status": "ok"}

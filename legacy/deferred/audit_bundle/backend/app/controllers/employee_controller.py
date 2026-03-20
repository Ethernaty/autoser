from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.controllers.schemas.employee_schemas import EmployeeCreateRequest, EmployeeResponse
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.feature_quota_guard import RequireQuota
from app.middleware.permission_guard import RequirePermission
from app.services.employee_service import EmployeeService


router = APIRouter(prefix="/users", tags=["Users"])


def get_employee_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> EmployeeService:
    return EmployeeService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.post(
    "/",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "create")), Depends(RequireQuota("users"))],
)
async def create_employee(
    payload: EmployeeCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = await service.create_employee(
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
        idempotency_key=idempotency_key,
    )
    return EmployeeResponse(
        user_id=employee.user_id,
        tenant_id=employee.tenant_id,
        email=employee.email,
        role=employee.role.value,
        is_active=employee.is_active,
        version=employee.version,
        created_at=employee.created_at,
    )

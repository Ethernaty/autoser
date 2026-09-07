from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.controllers.schemas.employee_schemas import (
    EmployeeCreateRequest,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeStatusRequest,
    EmployeeUpdateRequest,
)
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.employee_service import EmployeeRecord, EmployeeService


router = APIRouter(prefix="/employees", tags=["Employees"])
legacy_router = APIRouter(prefix="/users", tags=["Users (Deprecated)"])
MAX_LIMIT = get_settings().max_limit


def get_employee_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> EmployeeService:
    return EmployeeService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


def _to_response(employee: EmployeeRecord) -> EmployeeResponse:
    return EmployeeResponse(
        employee_id=employee.user_id,
        user_id=employee.user_id,
        tenant_id=employee.tenant_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.value,
        is_active=employee.is_active,
        job_title=employee.job_title,
        can_accept_payments=employee.can_accept_payments,
        version=employee.version,
        created_at=employee.created_at,
    )


@router.get("/", response_model=EmployeeListResponse, dependencies=[Depends(RequirePermission("employees", "read"))])
@legacy_router.get(
    "/",
    response_model=EmployeeListResponse,
    dependencies=[Depends(RequirePermission("employees", "read"))],
    include_in_schema=False,
)
async def list_employees(
    query: str | None = Query(default=None, alias="q"),
    role: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeListResponse:
    items = await service.list_employees_paginated(limit=limit, offset=offset, query=query, role=role)
    total = await service.count_employees(query=query, role=role)
    return EmployeeListResponse(
        items=[_to_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse, dependencies=[Depends(RequirePermission("employees", "read"))])
@legacy_router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "read"))],
    include_in_schema=False,
)
async def get_employee(employee_id: UUID, service: EmployeeService = Depends(get_employee_service)) -> EmployeeResponse:
    employee = await service.get_employee(user_id=employee_id)
    return _to_response(employee)


@router.post("/", response_model=EmployeeResponse, dependencies=[Depends(RequirePermission("employees", "create"))])
@legacy_router.post(
    "/",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "create"))],
    include_in_schema=False,
)
async def create_employee(
    payload: EmployeeCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = await service.create_employee(
        email=str(payload.email) if payload.email else None,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
        job_title=payload.job_title,
        can_accept_payments=payload.can_accept_payments,
        idempotency_key=idempotency_key,
    )
    return _to_response(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "update"))],
)
@legacy_router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "update"))],
    include_in_schema=False,
)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdateRequest,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = await service.update_employee(
        user_id=employee_id,
        full_name=payload.full_name,
        email=str(payload.email) if payload.email else None,
        password=payload.password,
        role=payload.role,
        is_active=payload.is_active,
        job_title=payload.job_title,
        can_accept_payments=payload.can_accept_payments,
    )
    return _to_response(employee)


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "update"))],
)
@legacy_router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
    dependencies=[Depends(RequirePermission("employees", "update"))],
    include_in_schema=False,
)
async def set_employee_status(
    employee_id: UUID,
    payload: EmployeeStatusRequest,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = await service.update_employee(
        user_id=employee_id,
        is_active=payload.is_active,
        job_title=payload.job_title,
        can_accept_payments=payload.can_accept_payments,
    )
    return _to_response(employee)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("employees", "delete"))],
)
@legacy_router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("employees", "delete"))],
    include_in_schema=False,
)
async def delete_employee(employee_id: UUID, service: EmployeeService = Depends(get_employee_service)) -> Response:
    await service.delete_employee(user_id=employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

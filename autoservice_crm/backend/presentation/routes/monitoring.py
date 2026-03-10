from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService, UserContext
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.auth_context import resolve_user_context
from presentation.services.monitoring_admin_service import (
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
    MonitoringAdminService,
)
from presentation.templating import templates


router = APIRouter()


def get_monitoring_admin_service() -> MonitoringAdminService:
    return MonitoringAdminService()


@router.get("/logs", response_class=HTMLResponse, name="admin_logs_page")
async def logs_page(
    request: Request,
    q: str = Query(default="", max_length=200),
    level: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auto_refresh: bool = Query(default=False),
    auth_service: AuthService = Depends(get_auth_service),
    monitoring_service: MonitoringAdminService = Depends(get_monitoring_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    await _audit_monitor_access(current_user=current_user, panel="logs", request=request)

    view = await monitoring_service.build_logs_page(
        tenant_id=current_user.tenant.id,
        q=q,
        level=level,
        page=page,
        per_page=per_page,
        auto_refresh=auto_refresh,
        errors_only=False,
    )
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "table_route": "/admin/logs/table",
            "page_route": "/admin/logs",
            "title": "System Logs",
            "allow_level_filter": True,
        },
    )


@router.get("/logs/table", response_class=HTMLResponse, name="admin_logs_table")
async def logs_table(
    request: Request,
    q: str = Query(default="", max_length=200),
    level: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auto_refresh: bool = Query(default=False),
    auth_service: AuthService = Depends(get_auth_service),
    monitoring_service: MonitoringAdminService = Depends(get_monitoring_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    view = await monitoring_service.build_logs_page(
        tenant_id=current_user.tenant.id,
        q=q,
        level=level,
        page=page,
        per_page=per_page,
        auto_refresh=auto_refresh,
        errors_only=False,
    )
    return templates.TemplateResponse(
        "monitoring_table.html",
        {
            "request": request,
            "view": view,
            "table_route": "/admin/logs/table",
            "page_route": "/admin/logs",
            "allow_level_filter": True,
        },
    )


@router.get("/errors", response_class=HTMLResponse, name="admin_errors_page")
async def errors_page(
    request: Request,
    q: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auto_refresh: bool = Query(default=True),
    auth_service: AuthService = Depends(get_auth_service),
    monitoring_service: MonitoringAdminService = Depends(get_monitoring_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    await _audit_monitor_access(current_user=current_user, panel="errors", request=request)

    view = await monitoring_service.build_logs_page(
        tenant_id=current_user.tenant.id,
        q=q,
        level="ERROR",
        page=page,
        per_page=per_page,
        auto_refresh=auto_refresh,
        errors_only=True,
    )
    return templates.TemplateResponse(
        "errors.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "table_route": "/admin/errors/table",
            "page_route": "/admin/errors",
            "title": "Error Logs",
            "allow_level_filter": False,
        },
    )


@router.get("/errors/table", response_class=HTMLResponse, name="admin_errors_table")
async def errors_table(
    request: Request,
    q: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auto_refresh: bool = Query(default=True),
    auth_service: AuthService = Depends(get_auth_service),
    monitoring_service: MonitoringAdminService = Depends(get_monitoring_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    view = await monitoring_service.build_logs_page(
        tenant_id=current_user.tenant.id,
        q=q,
        level="ERROR",
        page=page,
        per_page=per_page,
        auto_refresh=auto_refresh,
        errors_only=True,
    )
    return templates.TemplateResponse(
        "monitoring_table.html",
        {
            "request": request,
            "view": view,
            "table_route": "/admin/errors/table",
            "page_route": "/admin/errors",
            "allow_level_filter": False,
        },
    )


async def _resolve_current_user(request: Request, auth_service: AuthService) -> UserContext | RedirectResponse:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        return RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)

    try:
        return await resolve_user_context(auth_service=auth_service, access_token=access_token)
    except Exception:
        response = RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
        clear_auth_cookies(response)
        return response


def _enforce_admin(current_user: UserContext) -> RedirectResponse | None:
    if current_user.role.strip().lower() in {"owner", "admin"}:
        return None
    query = urlencode({"reason": "Admin monitoring requires owner/admin role."})
    return RedirectResponse(url=f"/admin/forbidden?{query}", status_code=303)


async def _audit_monitor_access(*, current_user: UserContext, panel: str, request: Request) -> None:
    audit_service = AuditLogService(tenant_id=current_user.tenant.id)
    await audit_service.log_action(
        user_id=current_user.user.id,
        action=f"admin.monitoring.{panel}.view",
        entity="audit_logs",
        entity_id=None,
        metadata={
            "panel": panel,
            "path": request.url.path,
            "query": dict(request.query_params),
            "actor_user_id": str(current_user.user.id),
            "actor_email": str(current_user.user.email),
        },
    )

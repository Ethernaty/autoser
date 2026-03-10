from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService, UserContext
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.auth_context import resolve_user_context
from presentation.services.system_metrics.service import SystemMetricsService, get_system_metrics_service
from presentation.templating import templates


router = APIRouter()


@router.get("/system", response_class=Response, name="admin_system_page")
async def system_page(
    request: Request,
    auto_refresh: bool = Query(default=True),
    auth_service: AuthService = Depends(get_auth_service),
    metrics_service: SystemMetricsService = Depends(get_system_metrics_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    await _audit_system_access(current_user=current_user, request=request)

    view = await metrics_service.build_dashboard_view(auto_refresh=auto_refresh)
    return templates.TemplateResponse(
        "system.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
        },
    )


@router.get("/system/widgets", response_class=Response, name="admin_system_widgets")
async def system_widgets(
    request: Request,
    auto_refresh: bool = Query(default=True),
    auth_service: AuthService = Depends(get_auth_service),
    metrics_service: SystemMetricsService = Depends(get_system_metrics_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    admin_gate = _enforce_admin(current_user)
    if admin_gate is not None:
        return admin_gate

    view = await metrics_service.build_dashboard_view(auto_refresh=auto_refresh)
    return templates.TemplateResponse(
        "system_widgets.html",
        {
            "request": request,
            "view": view,
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
    query = urlencode({"reason": "Admin system metrics require owner/admin role."})
    return RedirectResponse(url=f"/admin/forbidden?{query}", status_code=303)


async def _audit_system_access(*, current_user: UserContext, request: Request) -> None:
    audit_service = AuditLogService(tenant_id=current_user.tenant.id)
    await audit_service.log_action(
        user_id=current_user.user.id,
        action="admin.monitoring.system.view",
        entity="system_metrics",
        entity_id=None,
        metadata={
            "path": request.url.path,
            "query": dict(request.query_params),
            "actor_user_id": str(current_user.user.id),
            "actor_email": str(current_user.user.email),
        },
    )

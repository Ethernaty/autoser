from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.controllers.health_controller import health_ready
from app.core.exceptions import AppError
from app.services.auth_service import AuthService
from presentation.auth_context import resolve_user_context
from presentation.middleware import (
    ACCESS_COOKIE_NAME,
    ADMIN_DASHBOARD_PATH,
    ADMIN_LOGIN_PATH,
    clear_auth_cookies,
)
from presentation.templating import templates


router = APIRouter()


@router.get("/", include_in_schema=False)
async def admin_root() -> RedirectResponse:
    return RedirectResponse(url=ADMIN_DASHBOARD_PATH, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", response_class=HTMLResponse, name="admin_dashboard")
async def dashboard(request: Request, service: AuthService = Depends(get_auth_service)) -> Response:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        return RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)

    try:
        user_context = await resolve_user_context(auth_service=service, access_token=access_token)
    except AppError:
        response = RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
        clear_auth_cookies(response)
        return response

    system_status = await health_ready()
    server_time = datetime.now(UTC)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "system_status": system_status,
            "current_user": user_context,
            "server_time": server_time,
        },
    )

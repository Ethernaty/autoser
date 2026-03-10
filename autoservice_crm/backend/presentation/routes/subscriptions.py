from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.core.exceptions import AppError
from app.services.auth_service import AuthService, UserContext
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.auth_context import resolve_user_context
from presentation.services.subscriptions_admin_service import (
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
    SubscriptionsAdminService,
)
from presentation.templating import templates


router = APIRouter()


def get_subscriptions_admin_service() -> SubscriptionsAdminService:
    return SubscriptionsAdminService()


@router.get("/subscriptions", response_class=HTMLResponse, name="admin_subscriptions_page")
async def subscriptions_page(
    request: Request,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auth_service: AuthService = Depends(get_auth_service),
    subscriptions_admin_service: SubscriptionsAdminService = Depends(get_subscriptions_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await subscriptions_admin_service.build_list_view(
        q=q,
        page=page,
        per_page=per_page,
    )
    return templates.TemplateResponse(
        "subscriptions.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
        },
    )


@router.get("/subscriptions/table", response_class=HTMLResponse, name="admin_subscriptions_table")
async def subscriptions_table_partial(
    request: Request,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    subscriptions_admin_service: SubscriptionsAdminService = Depends(get_subscriptions_admin_service),
) -> HTMLResponse:
    view = await subscriptions_admin_service.build_list_view(
        q=q,
        page=page,
        per_page=per_page,
    )
    return templates.TemplateResponse(
        "subscriptions_table.html",
        {
            "request": request,
            "view": view,
        },
    )


@router.post("/subscriptions/{tenant_id}/cancel", response_class=HTMLResponse, name="admin_subscription_cancel")
async def cancel_subscription(
    request: Request,
    tenant_id: UUID,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auth_service: AuthService = Depends(get_auth_service),
    subscriptions_admin_service: SubscriptionsAdminService = Depends(get_subscriptions_admin_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    action_error: str | None = None
    try:
        await subscriptions_admin_service.cancel_subscription(
            tenant_id=tenant_id,
            actor_user_id=current_user.user.id,
            actor_role=current_user.role,
        )
    except AppError as exc:
        action_error = exc.message
    except Exception:
        action_error = "Unable to cancel subscription at the moment."

    view = await subscriptions_admin_service.build_list_view(
        q=q,
        page=page,
        per_page=per_page,
        action_error=action_error,
    )

    return templates.TemplateResponse(
        "subscriptions_table.html",
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
    except AppError:
        response = RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
        clear_auth_cookies(response)
        return response

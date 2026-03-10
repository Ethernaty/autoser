from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.controllers.auth_controller import get_auth_service
from app.services.auth_service import AuthService, UserContext
from presentation.middleware import ACCESS_COOKIE_NAME
from presentation.auth_context import resolve_user_context
from presentation.templating import templates


router = APIRouter()


@router.get("/forbidden", response_class=HTMLResponse, name="forbidden_page")
async def forbidden_page(
    request: Request,
    reason: str = Query(default="You do not have access to this section."),
    auth_service: AuthService = Depends(get_auth_service),
) -> HTMLResponse:
    current_user = await _resolve_user_optional(request=request, auth_service=auth_service)
    return templates.TemplateResponse(
        "forbidden.html",
        {
            "request": request,
            "current_user": current_user,
            "reason": reason,
            "next_path": str(request.query_params.get("next", "")),
        },
        status_code=403,
    )


async def _resolve_user_optional(request: Request, auth_service: AuthService) -> UserContext | None:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        return None
    try:
        return await resolve_user_context(auth_service=auth_service, access_token=access_token)
    except Exception:
        return None

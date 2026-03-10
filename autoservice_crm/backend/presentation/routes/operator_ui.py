from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.core.exceptions import AppError
from app.models.order import OrderStatus
from app.services.auth_service import AuthService, UserContext
from presentation.auth_context import resolve_user_context
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.services.operator_ui_service import OperatorUiService
from presentation.templating import templates


router = APIRouter()


DASHBOARD_PATH = "/app/operator/dashboard"


def get_operator_ui_service() -> OperatorUiService:
    return OperatorUiService()


@router.get("/", include_in_schema=False)
async def app_root() -> RedirectResponse:
    return RedirectResponse(url=DASHBOARD_PATH, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operator", include_in_schema=False)
async def operator_root() -> RedirectResponse:
    return RedirectResponse(url=DASHBOARD_PATH, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operator/dashboard", response_class=HTMLResponse, name="operator_dashboard")
async def operator_dashboard(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await ui_service.build_dashboard_view(user=current_user)
    return templates.TemplateResponse(
        "operator_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "active_screen": "dashboard",
            "error": str(request.query_params.get("error", "")),
            "ok": str(request.query_params.get("ok", "")),
        },
    )


@router.get("/operator/new-order", response_class=HTMLResponse, name="operator_new_order")
async def operator_new_order_page(
    request: Request,
    phone: str = Query(default="", max_length=32),
    client_name: str = Query(default="", max_length=200),
    description: str = Query(default="", max_length=5000),
    price: str = Query(default="", max_length=32),
    selected_client_id: str | None = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await ui_service.build_new_order_view(
        user=current_user,
        phone=phone,
        client_name=client_name,
        description=description,
        price=price,
        selected_client_id=selected_client_id,
    )
    return templates.TemplateResponse(
        "operator_new_order.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "active_screen": "new_order",
            "error": str(request.query_params.get("error", "")),
            "ok": str(request.query_params.get("ok", "")),
        },
    )


@router.post("/operator/new-order", response_class=HTMLResponse, name="operator_new_order_submit")
async def operator_new_order_submit(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    form = await request.form()
    phone = str(form.get("phone", "")).strip()
    client_name = str(form.get("client_name", "")).strip()
    description = str(form.get("description", "")).strip()
    price = str(form.get("price", "")).strip()
    selected_client_id = str(form.get("selected_client_id", "")).strip() or None

    try:
        order_id = await ui_service.create_new_order(
            user=current_user,
            phone=phone,
            client_name=client_name,
            description=description,
            price=price,
            selected_client_id=selected_client_id,
        )
    except AppError as exc:
        query = urlencode(
            {
                "phone": phone,
                "client_name": client_name,
                "description": description,
                "price": price,
                "selected_client_id": selected_client_id or "",
                "error": exc.message,
            }
        )
        return RedirectResponse(url=f"/app/operator/new-order?{query}", status_code=status.HTTP_303_SEE_OTHER)

    query = urlencode({"ok": f"Order {order_id} created"})
    return RedirectResponse(url=f"{DASHBOARD_PATH}?{query}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operator/client", response_class=HTMLResponse, name="operator_client_card")
async def operator_client_card(
    request: Request,
    q: str = Query(default="", max_length=120),
    client_id: str | None = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await ui_service.build_client_card_view(user=current_user, query=q, client_id=client_id)
    return templates.TemplateResponse(
        "operator_client_card.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "active_screen": "client",
            "error": str(request.query_params.get("error", "")),
            "ok": str(request.query_params.get("ok", "")),
        },
    )


@router.get("/operator/today", response_class=HTMLResponse, name="operator_today")
async def operator_today(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await ui_service.build_today_view(user=current_user)
    return templates.TemplateResponse(
        "operator_today.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "active_screen": "today",
            "error": str(request.query_params.get("error", "")),
            "ok": str(request.query_params.get("ok", "")),
        },
    )


@router.post("/operator/today/{order_id}/start", name="operator_start_order")
async def operator_start_order(
    order_id: UUID,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> RedirectResponse:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        await ui_service.set_order_status(user=current_user, order_id=order_id, status=OrderStatus.IN_PROGRESS)
        query = urlencode({"ok": "Order moved to in progress"})
    except AppError as exc:
        query = urlencode({"error": exc.message})

    return RedirectResponse(url=f"/app/operator/today?{query}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operator/today/{order_id}/ready", name="operator_ready_order")
async def operator_ready_order(
    order_id: UUID,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> RedirectResponse:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        await ui_service.set_order_status(user=current_user, order_id=order_id, status=OrderStatus.COMPLETED)
        query = urlencode({"ok": "Order marked as ready"})
    except AppError as exc:
        query = urlencode({"error": exc.message})

    return RedirectResponse(url=f"/app/operator/today?{query}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operator/cash-desk", response_class=HTMLResponse, name="operator_cash_desk")
async def operator_cash_desk(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await ui_service.build_cash_desk_view(user=current_user)
    return templates.TemplateResponse(
        "operator_cash_desk.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "active_screen": "cash_desk",
            "error": str(request.query_params.get("error", "")),
            "ok": str(request.query_params.get("ok", "")),
        },
    )


@router.post("/operator/cash-desk/{order_id}/pay", name="operator_pay_order")
async def operator_pay_order(
    order_id: UUID,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    ui_service: OperatorUiService = Depends(get_operator_ui_service),
) -> RedirectResponse:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        await ui_service.register_payment(user=current_user, order_id=order_id)
        query = urlencode({"ok": "Payment recorded"})
    except AppError as exc:
        query = urlencode({"error": exc.message})

    return RedirectResponse(url=f"/app/operator/cash-desk?{query}", status_code=status.HTTP_303_SEE_OTHER)


async def _resolve_current_user(request: Request, auth_service: AuthService) -> UserContext | RedirectResponse:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        return RedirectResponse(url=f"{ADMIN_LOGIN_PATH}?next={DASHBOARD_PATH}", status_code=status.HTTP_303_SEE_OTHER)

    try:
        return await resolve_user_context(auth_service=auth_service, access_token=access_token)
    except Exception:
        response = RedirectResponse(url=f"{ADMIN_LOGIN_PATH}?next={DASHBOARD_PATH}", status_code=status.HTTP_303_SEE_OTHER)
        clear_auth_cookies(response)
        return response

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.core.exceptions import AppError
from presentation.rbac import PermissionDenied, can as can_role, ensure_permission
from app.services.auth_service import AuthService, UserContext
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.auth_context import resolve_user_context
from presentation.services.crm_panel_service import (
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
    CrmPanelService,
)
from presentation.templating import templates


router = APIRouter()


def get_crm_panel_service() -> CrmPanelService:
    return CrmPanelService()


@router.get("/clients", response_class=HTMLResponse, name="app_clients_page")
async def clients_page(
    request: Request,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    modal: str | None = Query(default=None),
    edit_id: UUID | None = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="clients", action="read")
    if denied is not None:
        return denied

    view = await panel_service.build_clients_view(
        user=current_user,
        q=q,
        page=page,
        per_page=per_page,
        modal_mode=_normalize_modal(modal),
        edit_id=edit_id,
    )
    return templates.TemplateResponse(
        "app_clients.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "can_create": _has_permission(current_user, "clients", "create"),
            "can_update": _has_permission(current_user, "clients", "update"),
            "can_delete": _has_permission(current_user, "clients", "delete"),
            "page_error": None,
        },
    )


@router.post("/clients/create", response_class=HTMLResponse, name="app_clients_create")
async def clients_create(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="clients", action="create")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q",))

    values = {
        "name": str(form.get("name", "")),
        "phone": str(form.get("phone", "")),
        "email": str(form.get("email", "")),
        "comment": str(form.get("comment", "")),
    }

    try:
        await panel_service.create_client(
            user=current_user,
            name=values["name"],
            phone=values["phone"],
            email=values["email"],
            comment=values["comment"],
        )
    except AppError as exc:
        view = await panel_service.build_clients_view(
            user=current_user,
            q=q,
            page=page,
            per_page=per_page,
            modal_mode="create",
            modal_values=values,
            modal_error=exc.message,
        )
        return templates.TemplateResponse(
            "app_clients.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "clients", "create"),
                "can_update": _has_permission(current_user, "clients", "update"),
                "can_delete": _has_permission(current_user, "clients", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(url=_app_url("/app/clients", {"q": q, "page": str(page), "per_page": str(per_page)}), status_code=303)


@router.post("/clients/{client_id}/update", response_class=HTMLResponse, name="app_clients_update")
async def clients_update(
    request: Request,
    client_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="clients", action="update")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q",))

    values = {
        "name": str(form.get("name", "")),
        "phone": str(form.get("phone", "")),
        "email": str(form.get("email", "")),
        "comment": str(form.get("comment", "")),
        "version": str(form.get("version", "")),
    }
    version = _to_int(values["version"], default=0)

    try:
        await panel_service.update_client(
            user=current_user,
            client_id=client_id,
            name=values["name"],
            phone=values["phone"],
            email=values["email"],
            comment=values["comment"],
            version=(version if version > 0 else None),
        )
    except AppError as exc:
        view = await panel_service.build_clients_view(
            user=current_user,
            q=q,
            page=page,
            per_page=per_page,
            modal_mode="edit",
            edit_id=client_id,
            modal_values=values,
            modal_error=exc.message,
        )
        return templates.TemplateResponse(
            "app_clients.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "clients", "create"),
                "can_update": _has_permission(current_user, "clients", "update"),
                "can_delete": _has_permission(current_user, "clients", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(url=_app_url("/app/clients", {"q": q, "page": str(page), "per_page": str(per_page)}), status_code=303)


@router.post("/clients/{client_id}/delete", response_class=HTMLResponse, name="app_clients_delete")
async def clients_delete(
    request: Request,
    client_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="clients", action="delete")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q",))

    try:
        await panel_service.delete_client(user=current_user, client_id=client_id)
        return RedirectResponse(url=_app_url("/app/clients", {"q": q, "page": str(page), "per_page": str(per_page)}), status_code=303)
    except AppError as exc:
        view = await panel_service.build_clients_view(
            user=current_user,
            q=q,
            page=page,
            per_page=per_page,
        )
        return templates.TemplateResponse(
            "app_clients.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "clients", "create"),
                "can_update": _has_permission(current_user, "clients", "update"),
                "can_delete": _has_permission(current_user, "clients", "delete"),
                "page_error": exc.message,
            },
            status_code=400,
        )


@router.get("/orders", response_class=HTMLResponse, name="app_orders_page")
async def orders_page(
    request: Request,
    q: str = Query(default="", max_length=120),
    status_filter: str = Query(default="", alias="status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    modal: str | None = Query(default=None),
    edit_id: UUID | None = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="work_orders", action="read")
    if denied is not None:
        return denied

    view = await panel_service.build_orders_view(
        user=current_user,
        q=q,
        status_filter=status_filter,
        page=page,
        per_page=per_page,
        modal_mode=_normalize_modal(modal),
        edit_id=edit_id,
    )
    return templates.TemplateResponse(
        "app_orders.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "can_create": _has_permission(current_user, "work_orders", "create"),
            "can_update": _has_permission(current_user, "work_orders", "update"),
            "can_delete": _has_permission(current_user, "work_orders", "delete"),
            "page_error": None,
        },
    )


@router.post("/orders/create", response_class=HTMLResponse, name="app_orders_create")
async def orders_create(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="work_orders", action="create")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "status"))
    status_filter = str(form.get("status", "")) if "status" in form else ""

    values = {
        "client_id": str(form.get("client_id", "")),
        "description": str(form.get("description", "")),
        "price": str(form.get("price", "")),
        "status": str(form.get("order_status", "new")),
    }

    try:
        await panel_service.create_order(
            user=current_user,
            client_id=UUID(values["client_id"]),
            description=values["description"],
            price=Decimal(values["price"]),
            status=values["status"],
        )
    except (ValueError, AppError) as exc:
        message = exc.message if isinstance(exc, AppError) else "Invalid order form data"
        view = await panel_service.build_orders_view(
            user=current_user,
            q=q,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
            modal_mode="create",
            modal_values=values,
            modal_error=message,
        )
        return templates.TemplateResponse(
            "app_orders.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "work_orders", "create"),
                "can_update": _has_permission(current_user, "work_orders", "update"),
                "can_delete": _has_permission(current_user, "work_orders", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(
        url=_app_url(
            "/app/orders",
            {"q": q, "status": status_filter, "page": str(page), "per_page": str(per_page)},
        ),
        status_code=303,
    )


@router.post("/orders/{order_id}/update", response_class=HTMLResponse, name="app_orders_update")
async def orders_update(
    request: Request,
    order_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="work_orders", action="update")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "status"))
    status_filter = str(form.get("status", "")) if "status" in form else ""

    values = {
        "client_id": str(form.get("client_id", "")),
        "description": str(form.get("description", "")),
        "price": str(form.get("price", "")),
        "status": str(form.get("order_status", "new")),
    }

    try:
        await panel_service.update_order(
            user=current_user,
            order_id=order_id,
            description=values["description"],
            price=Decimal(values["price"]),
            status=values["status"],
        )
    except (ValueError, AppError) as exc:
        message = exc.message if isinstance(exc, AppError) else "Invalid order form data"
        view = await panel_service.build_orders_view(
            user=current_user,
            q=q,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
            modal_mode="edit",
            edit_id=order_id,
            modal_values=values,
            modal_error=message,
        )
        return templates.TemplateResponse(
            "app_orders.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "work_orders", "create"),
                "can_update": _has_permission(current_user, "work_orders", "update"),
                "can_delete": _has_permission(current_user, "work_orders", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(
        url=_app_url(
            "/app/orders",
            {"q": q, "status": status_filter, "page": str(page), "per_page": str(per_page)},
        ),
        status_code=303,
    )


@router.post("/orders/{order_id}/delete", response_class=HTMLResponse, name="app_orders_delete")
async def orders_delete(
    request: Request,
    order_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="work_orders", action="delete")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "status"))
    status_filter = str(form.get("status", "")) if "status" in form else ""

    try:
        await panel_service.delete_order(user=current_user, order_id=order_id)
        return RedirectResponse(
            url=_app_url(
                "/app/orders",
                {"q": q, "status": status_filter, "page": str(page), "per_page": str(per_page)},
            ),
            status_code=303,
        )
    except AppError as exc:
        view = await panel_service.build_orders_view(
            user=current_user,
            q=q,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
        )
        return templates.TemplateResponse(
            "app_orders.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "work_orders", "create"),
                "can_update": _has_permission(current_user, "work_orders", "update"),
                "can_delete": _has_permission(current_user, "work_orders", "delete"),
                "page_error": exc.message,
            },
            status_code=400,
        )


@router.get("/employees", response_class=HTMLResponse, name="app_employees_page")
async def employees_page(
    request: Request,
    q: str = Query(default="", max_length=120),
    role_filter: str = Query(default="", alias="role"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    modal: str | None = Query(default=None),
    edit_id: UUID | None = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="employees", action="read")
    if denied is not None:
        return denied

    view = await panel_service.build_employees_view(
        user=current_user,
        q=q,
        role_filter=role_filter,
        page=page,
        per_page=per_page,
        modal_mode=_normalize_modal(modal),
        edit_id=edit_id,
    )
    return templates.TemplateResponse(
        "app_employees.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "can_create": _has_permission(current_user, "employees", "create"),
            "can_update": _has_permission(current_user, "employees", "update"),
            "can_delete": _has_permission(current_user, "employees", "delete"),
            "page_error": None,
        },
    )


@router.post("/employees/create", response_class=HTMLResponse, name="app_employees_create")
async def employees_create(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="employees", action="create")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "role"))
    role_filter = str(form.get("role", "")) if "role" in form else ""

    values = {
        "email": str(form.get("email", "")),
        "password": str(form.get("password", "")),
        "role": str(form.get("employee_role", "employee")),
    }

    try:
        await panel_service.create_employee(
            user=current_user,
            email=values["email"],
            password=values["password"],
            role=values["role"],
        )
    except AppError as exc:
        view = await panel_service.build_employees_view(
            user=current_user,
            q=q,
            role_filter=role_filter,
            page=page,
            per_page=per_page,
            modal_mode="create",
            modal_values=values,
            modal_error=exc.message,
        )
        return templates.TemplateResponse(
            "app_employees.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "employees", "create"),
                "can_update": _has_permission(current_user, "employees", "update"),
                "can_delete": _has_permission(current_user, "employees", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(
        url=_app_url(
            "/app/employees",
            {"q": q, "role": role_filter, "page": str(page), "per_page": str(per_page)},
        ),
        status_code=303,
    )


@router.post("/employees/{user_id}/update", response_class=HTMLResponse, name="app_employees_update")
async def employees_update(
    request: Request,
    user_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="employees", action="update")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "role"))
    role_filter = str(form.get("role", "")) if "role" in form else ""

    values = {
        "email": str(form.get("email", "")),
        "password": str(form.get("password", "")),
        "role": str(form.get("employee_role", "employee")),
        "is_active": str(form.get("is_active", "true")),
    }

    try:
        await panel_service.update_employee(
            user=current_user,
            user_id=user_id,
            email=values["email"],
            password=values["password"],
            role=values["role"],
            is_active=values["is_active"].strip().lower() == "true",
        )
    except AppError as exc:
        view = await panel_service.build_employees_view(
            user=current_user,
            q=q,
            role_filter=role_filter,
            page=page,
            per_page=per_page,
            modal_mode="edit",
            edit_id=user_id,
            modal_values=values,
            modal_error=exc.message,
        )
        return templates.TemplateResponse(
            "app_employees.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "employees", "create"),
                "can_update": _has_permission(current_user, "employees", "update"),
                "can_delete": _has_permission(current_user, "employees", "delete"),
                "page_error": None,
            },
            status_code=400,
        )

    return RedirectResponse(
        url=_app_url(
            "/app/employees",
            {"q": q, "role": role_filter, "page": str(page), "per_page": str(per_page)},
        ),
        status_code=303,
    )


@router.post("/employees/{user_id}/delete", response_class=HTMLResponse, name="app_employees_delete")
async def employees_delete(
    request: Request,
    user_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
    panel_service: CrmPanelService = Depends(get_crm_panel_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    denied = _ensure_permission(current_user=current_user, resource="employees", action="delete")
    if denied is not None:
        return denied

    form = await request.form()
    q, page, per_page = _list_state(form, filters=("q", "role"))
    role_filter = str(form.get("role", "")) if "role" in form else ""

    try:
        await panel_service.delete_employee(user=current_user, user_id=user_id)
        return RedirectResponse(
            url=_app_url(
                "/app/employees",
                {"q": q, "role": role_filter, "page": str(page), "per_page": str(per_page)},
            ),
            status_code=303,
        )
    except AppError as exc:
        view = await panel_service.build_employees_view(
            user=current_user,
            q=q,
            role_filter=role_filter,
            page=page,
            per_page=per_page,
        )
        return templates.TemplateResponse(
            "app_employees.html",
            {
                "request": request,
                "current_user": current_user,
                "view": view,
                "can_create": _has_permission(current_user, "employees", "create"),
                "can_update": _has_permission(current_user, "employees", "update"),
                "can_delete": _has_permission(current_user, "employees", "delete"),
                "page_error": exc.message,
            },
            status_code=400,
        )


async def _resolve_current_user(request: Request, auth_service: AuthService) -> UserContext | RedirectResponse:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        return RedirectResponse(url=f"{ADMIN_LOGIN_PATH}?next=/app/clients", status_code=status.HTTP_303_SEE_OTHER)

    try:
        return await resolve_user_context(auth_service=auth_service, access_token=access_token)
    except Exception:
        response = RedirectResponse(url=f"{ADMIN_LOGIN_PATH}?next=/app/clients", status_code=status.HTTP_303_SEE_OTHER)
        clear_auth_cookies(response)
        return response


def _ensure_permission(*, current_user: UserContext, resource: str, action: str) -> RedirectResponse | None:
    try:
        ensure_permission(role=current_user.role, resource=resource, action=action)
        return None
    except PermissionDenied:
        from urllib.parse import urlencode

        reason = urlencode({"reason": f"Permission denied for {resource}:{action}"})
        return RedirectResponse(url=f"/app/forbidden?{reason}", status_code=303)


def _has_permission(current_user: UserContext, resource: str, action: str) -> bool:
    return can_role(role=current_user.role, resource=resource, action=action)


def _normalize_modal(value: str | None) -> str | None:
    if value in {"create", "edit"}:
        return value
    return None


def _to_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return parsed if parsed > 0 else default


def _list_state(form, *, filters: tuple[str, ...]) -> tuple[str, int, int]:  # noqa: ANN001
    q = str(form.get("q", "")).strip()
    page = _to_int(str(form.get("page", "1")), default=1)
    per_page = _to_int(str(form.get("per_page", str(DEFAULT_PER_PAGE))), default=DEFAULT_PER_PAGE)
    if "q" not in filters:
        q = ""
    return q, page, per_page


def _app_url(path: str, params: dict[str, str]) -> str:
    clean = {k: v for k, v in params.items() if v != ""}
    if not clean:
        return path
    from urllib.parse import urlencode

    return f"{path}?{urlencode(clean)}"



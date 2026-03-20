from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.controllers.auth_controller import get_auth_service
from app.core.exceptions import AppError
from app.models.tenant import Tenant
from app.services.auth_service import AuthService, UserContext
from app.services.subscription_service import SubscriptionService
from app.services.tenant_lifecycle_service import TenantLifecycleService
from presentation.middleware import ACCESS_COOKIE_NAME, ADMIN_LOGIN_PATH, clear_auth_cookies
from presentation.auth_context import resolve_user_context
from presentation.templating import templates


DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 50
SEARCH_SCAN_LIMIT = 2_000


@dataclass(frozen=True)
class TenantRowView:
    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    subscription_plan: str


@dataclass(frozen=True)
class TenantListView:
    rows: list[TenantRowView]
    q: str
    page: int
    per_page: int
    has_prev: bool
    has_next: bool


def get_tenant_lifecycle_service() -> TenantLifecycleService:
    return TenantLifecycleService()


router = APIRouter()


@router.get("/tenants", response_class=HTMLResponse, name="admin_tenants_page")
async def tenants_page(
    request: Request,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    auth_service: AuthService = Depends(get_auth_service),
    tenant_service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> Response:
    current_user = await _resolve_current_user(request=request, auth_service=auth_service)
    if isinstance(current_user, RedirectResponse):
        return current_user

    view = await _build_tenant_list_view(
        tenant_service=tenant_service,
        q=q,
        page=page,
        per_page=per_page,
    )

    return templates.TemplateResponse(
        "tenants.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
        },
    )


@router.get("/tenants/table", response_class=HTMLResponse, name="admin_tenants_table")
async def tenants_table_partial(
    request: Request,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    tenant_service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> HTMLResponse:
    view = await _build_tenant_list_view(
        tenant_service=tenant_service,
        q=q,
        page=page,
        per_page=per_page,
    )

    return templates.TemplateResponse(
        "tenants_table.html",
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


async def _build_tenant_list_view(
    *,
    tenant_service: TenantLifecycleService,
    q: str,
    page: int,
    per_page: int,
) -> TenantListView:
    normalized_query = q.strip().lower()
    safe_page = max(1, page)
    safe_per_page = max(1, min(per_page, MAX_PER_PAGE))

    tenants, has_next = await _list_tenants_page(
        tenant_service=tenant_service,
        q=normalized_query,
        page=safe_page,
        per_page=safe_per_page,
    )

    rows = await _to_rows(tenants)
    return TenantListView(
        rows=rows,
        q=normalized_query,
        page=safe_page,
        per_page=safe_per_page,
        has_prev=safe_page > 1,
        has_next=has_next,
    )


async def _list_tenants_page(
    *,
    tenant_service: TenantLifecycleService,
    q: str,
    page: int,
    per_page: int,
) -> tuple[list[Tenant], bool]:
    if not q:
        offset = (page - 1) * per_page
        chunk = await tenant_service.list_tenants(limit=per_page + 1, offset=offset)
        return chunk[:per_page], len(chunk) > per_page

    needed = (page * per_page) + 1
    matched: list[Tenant] = []
    scanned = 0
    offset = 0
    batch_size = max(per_page * 4, 50)

    while len(matched) < needed and scanned < SEARCH_SCAN_LIMIT:
        remaining_scan = SEARCH_SCAN_LIMIT - scanned
        limit = min(batch_size, remaining_scan)
        chunk = await tenant_service.list_tenants(limit=limit, offset=offset)
        if not chunk:
            break

        scanned += len(chunk)
        offset += len(chunk)

        for tenant in chunk:
            if _tenant_matches(tenant=tenant, q=q):
                matched.append(tenant)
                if len(matched) >= needed:
                    break

        if len(chunk) < limit:
            break

    start = (page - 1) * per_page
    end = start + per_page
    return matched[start:end], len(matched) > end


def _tenant_matches(*, tenant: Tenant, q: str) -> bool:
    haystack = " ".join(
        [
            str(tenant.id),
            tenant.name,
            tenant.slug,
            tenant.state.value if hasattr(tenant.state, "value") else str(tenant.state),
        ]
    ).lower()
    return q in haystack


async def _to_rows(tenants: Sequence[Tenant]) -> list[TenantRowView]:
    async def to_row(tenant: Tenant) -> TenantRowView:
        plan_name = await _resolve_subscription_plan_name(tenant_id=tenant.id)
        status_value = tenant.state.value if hasattr(tenant.state, "value") else str(tenant.state)
        return TenantRowView(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=status_value,
            created_at=tenant.created_at,
            subscription_plan=plan_name,
        )

    return list(await asyncio.gather(*(to_row(item) for item in tenants)))


async def _resolve_subscription_plan_name(*, tenant_id: UUID) -> str:
    service = SubscriptionService(tenant_id=tenant_id, actor_user_id=None, actor_role="owner")
    try:
        plan = await service.get_effective_plan()
        return plan.name
    except AppError as exc:
        if exc.code in {"subscription_not_found", "plan_not_found"}:
            return "n/a"
        return "unavailable"
    except Exception:
        return "unavailable"

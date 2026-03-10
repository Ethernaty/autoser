from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode
from uuid import UUID

from app.core.exceptions import AppError
from app.models.order import Order, OrderStatus
from app.services.auth_service import UserContext
from app.services.client_service import ClientService
from app.services.employee_service import EmployeeRecord, EmployeeService
from app.services.order_service import OrderService


DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 50
SEARCH_SCAN_LIMIT = 2_000


@dataclass(frozen=True)
class PaginationView:
    page: int
    per_page: int
    has_prev: bool
    has_next: bool
    prev_url: str | None
    next_url: str | None


@dataclass(frozen=True)
class ClientRowView:
    id: UUID
    name: str
    phone: str
    email: str | None
    comment: str | None
    version: int


@dataclass(frozen=True)
class ClientPageView:
    rows: list[ClientRowView]
    q: str
    pagination: PaginationView
    modal_mode: str | None
    modal_error: str | None
    modal_values: dict[str, str]
    edit_id: str | None
    close_modal_url: str


@dataclass(frozen=True)
class OrderRowView:
    id: UUID
    client_id: UUID
    client_name: str
    description: str
    price: Decimal
    status: str


@dataclass(frozen=True)
class OrderPageView:
    rows: list[OrderRowView]
    q: str
    status_filter: str
    pagination: PaginationView
    modal_mode: str | None
    modal_error: str | None
    modal_values: dict[str, str]
    edit_id: str | None
    close_modal_url: str
    status_options: tuple[str, ...]
    client_options: list[tuple[str, str]]


@dataclass(frozen=True)
class EmployeeRowView:
    user_id: UUID
    email: str
    role: str
    is_active: bool
    version: int


@dataclass(frozen=True)
class EmployeePageView:
    rows: list[EmployeeRowView]
    q: str
    role_filter: str
    pagination: PaginationView
    modal_mode: str | None
    modal_error: str | None
    modal_values: dict[str, str]
    edit_id: str | None
    close_modal_url: str
    role_options: tuple[str, ...]


class CrmPanelService:
    """Presentation orchestration for CRM /app panel pages."""

    async def build_clients_view(
        self,
        *,
        user: UserContext,
        q: str,
        page: int,
        per_page: int,
        modal_mode: str | None = None,
        edit_id: UUID | None = None,
        modal_values: dict[str, str] | None = None,
        modal_error: str | None = None,
    ) -> ClientPageView:
        normalized_q = q.strip()
        safe_page = max(1, page)
        safe_per_page = max(1, min(per_page, MAX_PER_PAGE))

        service = self._client_service(user)
        offset = (safe_page - 1) * safe_per_page
        if normalized_q:
            items = await service.search_clients(query=normalized_q, limit=safe_per_page + 1, offset=offset)
        else:
            items = await service.list_clients_paginated(limit=safe_per_page + 1, offset=offset)

        has_next = len(items) > safe_per_page
        rows = [
            ClientRowView(
                id=item.id,
                name=item.name,
                phone=item.phone,
                email=item.email,
                comment=item.comment,
                version=item.version,
            )
            for item in items[:safe_per_page]
        ]

        base_params = {
            "q": normalized_q,
            "page": str(safe_page),
            "per_page": str(safe_per_page),
        }
        pagination = self._build_pagination(
            base_path="/app/clients",
            page=safe_page,
            per_page=safe_per_page,
            has_next=has_next,
            base_params={"q": normalized_q, "per_page": str(safe_per_page)},
        )

        values = dict(modal_values or {})
        if modal_mode == "edit" and edit_id is not None and not values:
            current = await service.get_client(client_id=edit_id)
            values = {
                "name": current.name,
                "phone": current.phone,
                "email": current.email or "",
                "comment": current.comment or "",
                "version": str(current.version),
            }

        return ClientPageView(
            rows=rows,
            q=normalized_q,
            pagination=pagination,
            modal_mode=modal_mode,
            modal_error=modal_error,
            modal_values=values,
            edit_id=(str(edit_id) if edit_id is not None else None),
            close_modal_url=self._url_for("/app/clients", base_params),
        )

    async def create_client(self, *, user: UserContext, name: str, phone: str, email: str, comment: str) -> None:
        service = self._client_service(user)
        await service.create_client(
            name=name,
            phone=phone,
            email=email or None,
            comment=comment or None,
            idempotency_key=None,
        )

    async def update_client(
        self,
        *,
        user: UserContext,
        client_id: UUID,
        name: str,
        phone: str,
        email: str,
        comment: str,
        version: int | None,
    ) -> None:
        service = self._client_service(user)
        await service.update_client(
            client_id=client_id,
            name=name,
            phone=phone,
            email=email or None,
            comment=comment or None,
            expected_version=version,
        )

    async def delete_client(self, *, user: UserContext, client_id: UUID) -> None:
        service = self._client_service(user)
        await service.delete_client(client_id=client_id)

    async def build_orders_view(
        self,
        *,
        user: UserContext,
        q: str,
        status_filter: str,
        page: int,
        per_page: int,
        modal_mode: str | None = None,
        edit_id: UUID | None = None,
        modal_values: dict[str, str] | None = None,
        modal_error: str | None = None,
    ) -> OrderPageView:
        normalized_q = q.strip()
        normalized_status = self._normalize_status_filter(status_filter)
        safe_page = max(1, page)
        safe_per_page = max(1, min(per_page, MAX_PER_PAGE))

        order_service = self._order_service(user)
        orders, has_next = await self._list_orders_page(
            service=order_service,
            q=normalized_q,
            status_filter=normalized_status,
            page=safe_page,
            per_page=safe_per_page,
        )

        client_service = self._client_service(user)
        client_names = await self._resolve_client_names(client_service=client_service, orders=orders)

        rows = [
            OrderRowView(
                id=item.id,
                client_id=item.client_id,
                client_name=client_names.get(item.client_id, str(item.client_id)),
                description=item.description,
                price=item.price,
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
            )
            for item in orders
        ]

        client_options = await self._list_client_options(client_service=client_service)

        base_params = {
            "q": normalized_q,
            "status": normalized_status,
            "page": str(safe_page),
            "per_page": str(safe_per_page),
        }
        pagination = self._build_pagination(
            base_path="/app/orders",
            page=safe_page,
            per_page=safe_per_page,
            has_next=has_next,
            base_params={
                "q": normalized_q,
                "status": normalized_status,
                "per_page": str(safe_per_page),
            },
        )

        values = dict(modal_values or {})
        if modal_mode == "edit" and edit_id is not None and not values:
            current = await order_service.get_order(order_id=edit_id)
            values = {
                "client_id": str(current.client_id),
                "description": current.description,
                "price": str(current.price),
                "status": current.status.value if hasattr(current.status, "value") else str(current.status),
            }

        return OrderPageView(
            rows=rows,
            q=normalized_q,
            status_filter=normalized_status,
            pagination=pagination,
            modal_mode=modal_mode,
            modal_error=modal_error,
            modal_values=values,
            edit_id=(str(edit_id) if edit_id is not None else None),
            close_modal_url=self._url_for("/app/orders", base_params),
            status_options=tuple(item.value for item in OrderStatus),
            client_options=client_options,
        )

    async def create_order(
        self,
        *,
        user: UserContext,
        client_id: UUID,
        description: str,
        price: Decimal,
        status: str,
    ) -> None:
        service = self._order_service(user)
        await service.create_order(
            client_id=client_id,
            description=description,
            price=price,
            status=OrderStatus(status),
        )

    async def update_order(
        self,
        *,
        user: UserContext,
        order_id: UUID,
        description: str,
        price: Decimal,
        status: str,
    ) -> None:
        service = self._order_service(user)
        await service.update_order(
            order_id=order_id,
            description=description,
            price=price,
            status=OrderStatus(status),
        )

    async def delete_order(self, *, user: UserContext, order_id: UUID) -> None:
        service = self._order_service(user)
        await service.delete_order(order_id=order_id)

    async def build_employees_view(
        self,
        *,
        user: UserContext,
        q: str,
        role_filter: str,
        page: int,
        per_page: int,
        modal_mode: str | None = None,
        edit_id: UUID | None = None,
        modal_values: dict[str, str] | None = None,
        modal_error: str | None = None,
    ) -> EmployeePageView:
        normalized_q = q.strip()
        role_candidate = role_filter.strip().lower()
        normalized_role = role_candidate if role_candidate in {"owner", "admin", "manager", "employee"} else ""
        safe_page = max(1, page)
        safe_per_page = max(1, min(per_page, MAX_PER_PAGE))

        service = self._employee_service(user)
        offset = (safe_page - 1) * safe_per_page
        items = await service.list_employees_paginated(
            limit=safe_per_page + 1,
            offset=offset,
            query=normalized_q or None,
            role=normalized_role or None,
        )

        has_next = len(items) > safe_per_page
        rows = [
            EmployeeRowView(
                user_id=item.user_id,
                email=item.email,
                role=item.role.value,
                is_active=item.is_active,
                version=item.version,
            )
            for item in items[:safe_per_page]
        ]

        base_params = {
            "q": normalized_q,
            "role": normalized_role,
            "page": str(safe_page),
            "per_page": str(safe_per_page),
        }
        pagination = self._build_pagination(
            base_path="/app/employees",
            page=safe_page,
            per_page=safe_per_page,
            has_next=has_next,
            base_params={
                "q": normalized_q,
                "role": normalized_role,
                "per_page": str(safe_per_page),
            },
        )

        values = dict(modal_values or {})
        if modal_mode == "edit" and edit_id is not None and not values:
            current = await service.get_employee(user_id=edit_id)
            values = {
                "email": current.email,
                "role": current.role.value,
                "is_active": "true" if current.is_active else "false",
                "password": "",
            }

        return EmployeePageView(
            rows=rows,
            q=normalized_q,
            role_filter=normalized_role,
            pagination=pagination,
            modal_mode=modal_mode,
            modal_error=modal_error,
            modal_values=values,
            edit_id=(str(edit_id) if edit_id is not None else None),
            close_modal_url=self._url_for("/app/employees", base_params),
            role_options=("owner", "admin", "manager", "employee"),
        )

    async def create_employee(self, *, user: UserContext, email: str, password: str, role: str) -> None:
        service = self._employee_service(user)
        await service.create_employee(email=email, password=password, role=role)

    async def update_employee(
        self,
        *,
        user: UserContext,
        user_id: UUID,
        email: str,
        password: str,
        role: str,
        is_active: bool,
    ) -> None:
        service = self._employee_service(user)
        await service.update_employee(
            user_id=user_id,
            email=email,
            password=password or None,
            role=role,
            is_active=is_active,
        )

    async def delete_employee(self, *, user: UserContext, user_id: UUID) -> None:
        service = self._employee_service(user)
        await service.delete_employee(user_id=user_id)

    async def _list_orders_page(
        self,
        *,
        service: OrderService,
        q: str,
        status_filter: str,
        page: int,
        per_page: int,
    ) -> tuple[list[Order], bool]:
        if not status_filter:
            offset = (page - 1) * per_page
            if q:
                chunk = await service.search_orders(query=q, limit=per_page + 1, offset=offset)
            else:
                chunk = await service.list_orders_paginated(limit=per_page + 1, offset=offset)
            return chunk[:per_page], len(chunk) > per_page

        needed = (page * per_page) + 1
        matched: list[Order] = []
        scanned = 0
        offset = 0
        batch_size = max(per_page * 4, 50)

        while len(matched) < needed and scanned < SEARCH_SCAN_LIMIT:
            remaining_scan = SEARCH_SCAN_LIMIT - scanned
            limit = min(batch_size, remaining_scan)
            if q:
                chunk = await service.search_orders(query=q, limit=limit, offset=offset)
            else:
                chunk = await service.list_orders_paginated(limit=limit, offset=offset)

            if not chunk:
                break

            scanned += len(chunk)
            offset += len(chunk)

            for item in chunk:
                current_status = item.status.value if hasattr(item.status, "value") else str(item.status)
                if current_status == status_filter:
                    matched.append(item)
                    if len(matched) >= needed:
                        break

            if len(chunk) < limit:
                break

        start = (page - 1) * per_page
        end = start + per_page
        return matched[start:end], len(matched) > end

    async def _list_client_options(self, *, client_service: ClientService) -> list[tuple[str, str]]:
        # Keep provider constraints (max 50 rows per call) while collecting enough options for order forms.
        options: list[tuple[str, str]] = []
        offset = 0
        page_size = MAX_PER_PAGE

        while len(options) < 200:
            chunk = await client_service.list_clients_paginated(limit=page_size, offset=offset)
            if not chunk:
                break

            options.extend((str(client.id), client.name) for client in chunk)
            if len(chunk) < page_size:
                break

            offset += len(chunk)

        return options[:200]

    async def _resolve_client_names(
        self,
        *,
        client_service: ClientService,
        orders: list[Order],
    ) -> dict[UUID, str]:
        unique_ids = {item.client_id for item in orders}

        async def fetch_name(client_id: UUID) -> tuple[UUID, str | None]:
            try:
                client = await client_service.get_client(client_id=client_id)
                return client_id, client.name
            except Exception:
                return client_id, None

        pairs = await asyncio.gather(*(fetch_name(client_id) for client_id in unique_ids))
        return {client_id: name for client_id, name in pairs if name}

    @staticmethod
    def _normalize_status_filter(value: str) -> str:
        candidate = value.strip().lower()
        valid = {item.value for item in OrderStatus}
        return candidate if candidate in valid else ""

    @staticmethod
    def _build_pagination(
        *,
        base_path: str,
        page: int,
        per_page: int,
        has_next: bool,
        base_params: dict[str, str],
    ) -> PaginationView:
        clean_params = {key: value for key, value in base_params.items() if value != ""}
        has_prev = page > 1

        prev_url = None
        if has_prev:
            prev_params = dict(clean_params)
            prev_params["page"] = str(page - 1)
            prev_url = CrmPanelService._url_for(base_path, prev_params)

        next_url = None
        if has_next:
            next_params = dict(clean_params)
            next_params["page"] = str(page + 1)
            next_url = CrmPanelService._url_for(base_path, next_params)

        return PaginationView(
            page=page,
            per_page=per_page,
            has_prev=has_prev,
            has_next=has_next,
            prev_url=prev_url,
            next_url=next_url,
        )

    @staticmethod
    def _url_for(path: str, params: dict[str, str]) -> str:
        clean = {key: value for key, value in params.items() if value != "" and value is not None}
        if not clean:
            return path
        return f"{path}?{urlencode(clean)}"

    @staticmethod
    def _client_service(user: UserContext) -> ClientService:
        return ClientService(
            tenant_id=user.tenant.id,
            actor_user_id=user.user.id,
            actor_role=user.role,
        )

    @staticmethod
    def _order_service(user: UserContext) -> OrderService:
        return OrderService(
            tenant_id=user.tenant.id,
            actor_user_id=user.user.id,
            actor_role=user.role,
        )

    @staticmethod
    def _employee_service(user: UserContext) -> EmployeeService:
        return EmployeeService(
            tenant_id=user.tenant.id,
            actor_user_id=user.user.id,
            actor_role=user.role,
        )





from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.exceptions import AppError
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.services.auth_service import UserContext
from app.services.client_service import ClientService
from app.services.order_service import OrderService


MAX_SCAN = 200


@dataclass(frozen=True)
class OperatorOrderCard:
    id: UUID
    client_id: UUID
    client_name: str
    description: str
    price: Decimal
    status: str
    created_at: datetime
    overdue: bool


@dataclass(frozen=True)
class OperatorDashboardView:
    now_label: str
    in_progress_count: int
    waiting_count: int
    ready_count: int
    cash_count: int
    recent_orders: list[OperatorOrderCard]


@dataclass(frozen=True)
class OperatorNewOrderView:
    phone: str
    client_name: str
    description: str
    price: str
    selected_client_id: str | None
    suggestions: list[Client]


@dataclass(frozen=True)
class OperatorClientCardView:
    query: str
    selected_client: Client | None
    matches: list[Client]
    history_orders: list[OperatorOrderCard]


@dataclass(frozen=True)
class OperatorTodayView:
    now_label: str
    in_progress: list[OperatorOrderCard]
    waiting: list[OperatorOrderCard]
    overdue: list[OperatorOrderCard]
    ready: list[OperatorOrderCard]


@dataclass(frozen=True)
class OperatorCashDeskView:
    now_label: str
    total_due: Decimal
    rows: list[OperatorOrderCard]


class OperatorUiService:
    """Action-first operator UX service for fast auto-shop workflows."""

    async def build_dashboard_view(self, *, user: UserContext) -> OperatorDashboardView:
        cards = await self._list_order_cards(user=user, limit=50)
        in_progress = sum(1 for item in cards if item.status == OrderStatus.IN_PROGRESS.value)
        waiting = sum(1 for item in cards if item.status == OrderStatus.NEW.value)
        ready = sum(1 for item in cards if item.status == OrderStatus.COMPLETED.value)

        now = datetime.now(UTC)
        cash_due = [
            item
            for item in cards
            if item.status == OrderStatus.COMPLETED.value and now - item.created_at < timedelta(days=3)
        ]

        return OperatorDashboardView(
            now_label=now.astimezone().strftime("%d.%m.%Y %H:%M"),
            in_progress_count=in_progress,
            waiting_count=waiting,
            ready_count=ready,
            cash_count=len(cash_due),
            recent_orders=cards[:8],
        )

    async def build_new_order_view(
        self,
        *,
        user: UserContext,
        phone: str,
        client_name: str,
        description: str,
        price: str,
        selected_client_id: str | None,
    ) -> OperatorNewOrderView:
        normalized_phone = phone.strip()
        normalized_name = client_name.strip()
        matches: list[Client] = []

        lookup_query = normalized_phone or normalized_name
        if lookup_query:
            matches = await self._client_service(user).search_clients(query=lookup_query, limit=6, offset=0)

        return OperatorNewOrderView(
            phone=normalized_phone,
            client_name=normalized_name,
            description=description.strip(),
            price=price.strip(),
            selected_client_id=selected_client_id,
            suggestions=matches,
        )

    async def create_new_order(
        self,
        *,
        user: UserContext,
        phone: str,
        client_name: str,
        description: str,
        price: str,
        selected_client_id: str | None,
    ) -> UUID:
        normalized_phone = phone.strip()
        normalized_name = client_name.strip()
        normalized_description = description.strip()

        if not normalized_phone:
            raise AppError(status_code=400, code="invalid_phone", message="Phone is required")
        if not normalized_description:
            raise AppError(status_code=400, code="invalid_description", message="Order description is required")

        try:
            normalized_price = Decimal(price)
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_price", message="Invalid price format") from exc

        client_service = self._client_service(user)
        if selected_client_id:
            try:
                selected_id = UUID(selected_client_id)
            except Exception as exc:
                raise AppError(status_code=400, code="invalid_client", message="Invalid selected client id") from exc
            client = await client_service.get_client(client_id=selected_id)
        else:
            existing = await client_service.search_clients(query=normalized_phone, limit=1, offset=0)
            if existing:
                client = existing[0]
            else:
                suffix = normalized_phone[-4:] if len(normalized_phone) >= 4 else normalized_phone
                fallback_name = normalized_name or f"Client {suffix}"
                client = await client_service.create_client(
                    name=fallback_name,
                    phone=normalized_phone,
                    email=None,
                    comment="Created from operator quick order",
                    idempotency_key=None,
                )

        order = await self._order_service(user).create_order(
            client_id=client.id,
            description=normalized_description,
            price=normalized_price,
            status=OrderStatus.NEW,
        )
        return order.id

    async def build_client_card_view(
        self,
        *,
        user: UserContext,
        query: str,
        client_id: str | None,
    ) -> OperatorClientCardView:
        normalized_query = query.strip()
        matches: list[Client] = []
        selected: Client | None = None

        client_service = self._client_service(user)
        if normalized_query:
            matches = await client_service.search_clients(query=normalized_query, limit=8, offset=0)
            if matches:
                selected = matches[0]

        if client_id:
            try:
                selected = await client_service.get_client(client_id=UUID(client_id))
            except Exception:
                # Keep best-effort selected client from search result.
                pass

        history: list[OperatorOrderCard] = []
        if selected is not None:
            history = await self._orders_for_client(user=user, client_id=selected.id, limit=8)

        return OperatorClientCardView(
            query=normalized_query,
            selected_client=selected,
            matches=matches,
            history_orders=history,
        )

    async def build_today_view(self, *, user: UserContext) -> OperatorTodayView:
        now = datetime.now(UTC)
        cards = await self._list_order_cards(user=user, limit=80)

        in_progress = [item for item in cards if item.status == OrderStatus.IN_PROGRESS.value]
        waiting = [item for item in cards if item.status == OrderStatus.NEW.value]
        overdue = [item for item in waiting if item.created_at < now - timedelta(hours=3)]
        ready = [item for item in cards if item.status == OrderStatus.COMPLETED.value]

        return OperatorTodayView(
            now_label=now.astimezone().strftime("%d.%m.%Y %H:%M"),
            in_progress=in_progress[:12],
            waiting=waiting[:12],
            overdue=overdue[:12],
            ready=ready[:12],
        )

    async def set_order_status(self, *, user: UserContext, order_id: UUID, status: OrderStatus) -> None:
        await self._order_service(user).update_order(order_id=order_id, status=status)

    async def build_cash_desk_view(self, *, user: UserContext) -> OperatorCashDeskView:
        now = datetime.now(UTC)
        cards = await self._list_order_cards(user=user, limit=100)
        rows = [item for item in cards if item.status == OrderStatus.COMPLETED.value][:20]

        total_due = Decimal("0")
        for row in rows:
            total_due += row.price

        return OperatorCashDeskView(
            now_label=now.astimezone().strftime("%d.%m.%Y %H:%M"),
            total_due=total_due,
            rows=rows,
        )

    async def register_payment(self, *, user: UserContext, order_id: UUID) -> None:
        await self._order_service(user).update_order(order_id=order_id, status=OrderStatus.COMPLETED)

    async def _list_order_cards(self, *, user: UserContext, limit: int) -> list[OperatorOrderCard]:
        service = self._order_service(user)
        page_size = min(50, max(1, limit))
        offset = 0
        orders: list[Order] = []

        while len(orders) < limit and offset < MAX_SCAN:
            chunk = await service.list_orders_paginated(limit=page_size, offset=offset)
            if not chunk:
                break
            orders.extend(chunk)
            if len(chunk) < page_size:
                break
            offset += len(chunk)

        orders = orders[:limit]
        client_names = await self._resolve_client_names(user=user, orders=orders)

        now = datetime.now(UTC)
        cards: list[OperatorOrderCard] = []
        for item in orders:
            status_value = item.status.value if hasattr(item.status, "value") else str(item.status)
            cards.append(
                OperatorOrderCard(
                    id=item.id,
                    client_id=item.client_id,
                    client_name=client_names.get(item.client_id, "Unknown client"),
                    description=item.description,
                    price=item.price,
                    status=status_value,
                    created_at=item.created_at,
                    overdue=status_value == OrderStatus.NEW.value and item.created_at < now - timedelta(hours=3),
                )
            )

        cards.sort(key=lambda row: row.created_at, reverse=True)
        return cards

    async def _orders_for_client(self, *, user: UserContext, client_id: UUID, limit: int) -> list[OperatorOrderCard]:
        cards = await self._list_order_cards(user=user, limit=120)
        return [item for item in cards if item.client_id == client_id][:limit]

    async def _resolve_client_names(self, *, user: UserContext, orders: list[Order]) -> dict[UUID, str]:
        service = self._client_service(user)
        unique_ids = {item.client_id for item in orders}

        async def fetch_name(client_id: UUID) -> tuple[UUID, str]:
            try:
                client = await service.get_client(client_id=client_id)
                return client_id, client.name
            except Exception:
                return client_id, "Unknown client"

        pairs = await asyncio.gather(*(fetch_name(client_id) for client_id in unique_ids))
        return {client_id: name for client_id, name in pairs}

    @staticmethod
    def _client_service(user: UserContext) -> ClientService:
        return ClientService(tenant_id=user.tenant.id, actor_user_id=user.user.id, actor_role=user.role)

    @staticmethod
    def _order_service(user: UserContext) -> OrderService:
        return OrderService(tenant_id=user.tenant.id, actor_user_id=user.user.id, actor_role=user.role)

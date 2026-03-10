from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError, CrossTenantDataViolation
from app.core.input_security import guard_against_sqli, sanitize_text
from app.core.serialization import JsonSerializer, Serializer
from app.models.order import Order, OrderStatus
from app.repositories.client_repository import ClientRepository
from app.repositories.order_repository import OrderRepository
from app.services.audit_decorator import audit
from app.services.audit_log_service import AuditLogService
from app.services.base_service import BaseService
from app.services.idempotency_service import IdempotencyDecision, IdempotencyService


_CACHE_MISS = object()
_NAMESPACE_TTL_SECONDS = 60 * 60 * 24 * 30


class OrderService(BaseService):
    """Business service for tenant-scoped orders."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        settings = get_settings()
        self.max_limit = settings.max_limit
        self.cache_ttl_seconds = settings.client_cache_ttl_seconds
        self.negative_cache_ttl_seconds = settings.negative_cache_ttl_seconds

        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )
        self.audit_service = AuditLogService(tenant_id=tenant_id, session_factory=self._session_factory)
        self.idempotency_service = IdempotencyService(self)

    @audit(action="create", entity="order")
    async def create_order(
        self,
        *,
        client_id: UUID,
        description: str,
        price: Decimal,
        status: OrderStatus = OrderStatus.NEW,
        idempotency_key: str | None = None,
    ) -> Order:
        normalized_description = self._normalize_description(description)
        normalized_price = self._normalize_price(price)
        normalized_status = self._normalize_status(status)

        idempotency_decision: IdempotencyDecision | None = None
        if idempotency_key and idempotency_key.strip() and self.actor_user_id is not None:
            payload_hash = self.idempotency_service.build_request_hash(
                {
                    "client_id": str(client_id),
                    "description": normalized_description,
                    "price": str(normalized_price),
                    "status": normalized_status.value,
                }
            )
            idempotency_decision = await self.idempotency_service.begin(
                tenant_id=self.tenant_id,
                actor_id=self.actor_user_id,
                route="POST:/orders",
                key=idempotency_key.strip()[:128],
                request_hash=payload_hash,
            )
            if not idempotency_decision.proceed:
                if not isinstance(idempotency_decision.response_payload, dict):
                    raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
                return self._payload_to_order(idempotency_decision.response_payload)

        def write_op(db: Session) -> dict[str, Any]:
            client_repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            if client_repo.get_by_id(client_id) is None:
                raise AppError(status_code=404, code="client_not_found", message="Client not found")

            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            order = repo.create(
                client_id=client_id,
                description=normalized_description,
                price=normalized_price,
                status=normalized_status,
            )
            return self._order_to_payload(order)

        try:
            payload = await self.execute_write(write_op, idempotent=False)
        except Exception:
            if idempotency_decision and idempotency_decision.record_id is not None:
                await self._safe_mark_idempotency_failed(idempotency_decision.record_id)
            raise

        if idempotency_decision and idempotency_decision.record_id is not None:
            await self.idempotency_service.mark_succeeded(
                tenant_id=self.tenant_id,
                record_id=idempotency_decision.record_id,
                response_payload=payload,
            )
        await self._bump_namespace_version()
        return self._payload_to_order(payload)

    async def get_order(self, *, order_id: UUID) -> Order:
        namespace = await self._get_namespace_version()
        key = self._order_cache_key(order_id=order_id, namespace=namespace)

        async def loader() -> dict[str, Any] | None:
            def read_op(db: Session) -> dict[str, Any] | None:
                repo = OrderRepository(db=db, tenant_id=self.tenant_id)
                order = repo.get_by_id(order_id)
                if order is None:
                    return None
                return self._order_to_payload(order)

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader, negative_ttl=self.negative_cache_ttl_seconds)
        if payload is None:
            raise AppError(status_code=404, code="order_not_found", message="Order not found")
        return self._payload_to_order(payload)

    async def list_orders_paginated(self, *, limit: int, offset: int) -> list[Order]:
        self._validate_pagination(limit=limit, offset=offset)
        namespace = await self._get_namespace_version()
        key = self._list_cache_key(limit=limit, offset=offset, namespace=namespace)

        async def loader() -> list[dict[str, Any]]:
            def read_op(db: Session) -> list[dict[str, Any]]:
                repo = OrderRepository(db=db, tenant_id=self.tenant_id)
                return [self._order_to_payload(order) for order in repo.paginate(limit=limit, offset=offset)]

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        if not isinstance(payload, list):
            return []
        return [self._payload_to_order(item) for item in payload if isinstance(item, dict)]

    async def search_orders(self, *, query: str, limit: int, offset: int) -> list[Order]:
        self._validate_pagination(limit=limit, offset=offset)
        normalized_query = guard_against_sqli(query.strip())[:100]
        if not normalized_query:
            return await self.list_orders_paginated(limit=limit, offset=offset)

        namespace = await self._get_namespace_version()
        key = self._search_cache_key(query=normalized_query, limit=limit, offset=offset, namespace=namespace)

        async def loader() -> list[dict[str, Any]]:
            def read_op(db: Session) -> list[dict[str, Any]]:
                repo = OrderRepository(db=db, tenant_id=self.tenant_id)
                return [
                    self._order_to_payload(order)
                    for order in repo.search(query=normalized_query, limit=limit, offset=offset)
                ]

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        if not isinstance(payload, list):
            return []
        return [self._payload_to_order(item) for item in payload if isinstance(item, dict)]

    async def count_orders(self, *, query: str | None = None) -> int:
        normalized_query = guard_against_sqli(query.strip())[:100] if query else None
        namespace = await self._get_namespace_version()
        key = self._count_cache_key(query=normalized_query, namespace=namespace)

        async def loader() -> int:
            def read_op(db: Session) -> int:
                repo = OrderRepository(db=db, tenant_id=self.tenant_id)
                return repo.count(query=normalized_query)

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        return int(payload)

    @audit(action="update", entity="order")
    async def update_order(
        self,
        *,
        order_id: UUID,
        description: str | None = None,
        price: Decimal | None = None,
        status: OrderStatus | None = None,
    ) -> Order:
        updates: dict[str, object] = {}
        if description is not None:
            updates["description"] = self._normalize_description(description)
        if price is not None:
            updates["price"] = self._normalize_price(price)
        if status is not None:
            updates["status"] = self._normalize_status(status)

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> dict[str, Any]:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            order = repo.update(order_id, **updates)
            if order is None:
                raise AppError(status_code=404, code="order_not_found", message="Order not found")
            return self._order_to_payload(order)

        payload = await self.execute_write(write_op, idempotent=False)
        await self._bump_namespace_version()
        return self._payload_to_order(payload)

    @audit(action="delete", entity="order")
    async def delete_order(self, *, order_id: UUID) -> None:
        def write_op(db: Session) -> bool:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            return repo.delete_by_id(order_id)

        deleted = await self.execute_write(write_op, idempotent=False)
        if not deleted:
            raise AppError(status_code=404, code="order_not_found", message="Order not found")
        await self._bump_namespace_version()

    async def _cached_or_load(self, *, key: str, loader, negative_ttl: int | None = None):
        cached = await self._safe_cache_get(key)
        if cached is not _CACHE_MISS:
            if isinstance(cached, dict) and cached.get("__negative") is True:
                return None
            return cached

        lock = await self.get_singleflight_lock(key)
        async with lock:
            cached = await self._safe_cache_get(key)
            if cached is not _CACHE_MISS:
                if isinstance(cached, dict) and cached.get("__negative") is True:
                    return None
                return cached

            value = await loader()
            if value is None and negative_ttl is not None:
                await self._safe_cache_set(key, {"__negative": True}, ttl_seconds=negative_ttl)
                return None

            await self._safe_cache_set(key, value, ttl_seconds=self.cache_ttl_seconds)
            return value

    async def _safe_cache_get(self, key: str):
        self._assert_tenant_cache_key(key)
        try:
            raw = await self.cache.get(key)
        except Exception:
            return _CACHE_MISS

        if raw is None:
            return _CACHE_MISS

        if isinstance(raw, str):
            try:
                value = self.serializer.loads(raw)
                return await self.enforce_cache_payload_tenant(key=key, payload=value)
            except CrossTenantDataViolation:
                raise
            except Exception:
                return _CACHE_MISS

        try:
            return await self.enforce_cache_payload_tenant(key=key, payload=raw)
        except CrossTenantDataViolation:
            raise
        except Exception:
            return _CACHE_MISS

    async def _safe_cache_set(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        self._assert_tenant_cache_key(key)
        try:
            await self.cache.set(key, self.serializer.dumps(value), ttl_seconds)
        except Exception:
            return

    async def _get_namespace_version(self) -> int:
        key = self._namespace_version_key()
        self._assert_tenant_cache_key(key)
        try:
            raw = await self.cache.get(key)
            if raw is None:
                await self.cache.set_if_absent(key, 1, _NAMESPACE_TTL_SECONDS)
                return 1
            return int(raw)
        except Exception:
            return 1

    async def _bump_namespace_version(self) -> None:
        key = self._namespace_version_key()
        self._assert_tenant_cache_key(key)
        try:
            await self.cache.increment(key, 1, _NAMESPACE_TTL_SECONDS)
        except Exception:
            return

    async def _safe_mark_idempotency_failed(self, record_id: UUID) -> None:
        try:
            await self.idempotency_service.mark_failed(tenant_id=self.tenant_id, record_id=record_id)
        except Exception:
            return

    def _namespace_version_key(self) -> str:
        return f"tenant:{self.tenant_id}:orders:namespace"

    def _order_cache_key(self, *, order_id: UUID, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:orders:v{namespace}:get:{order_id}"

    def _list_cache_key(self, *, limit: int, offset: int, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:orders:v{namespace}:list:{limit}:{offset}"

    def _count_cache_key(self, *, query: str | None, namespace: int) -> str:
        normalized_query = quote_plus(query) if query else "_all"
        return f"tenant:{self.tenant_id}:orders:v{namespace}:count:{normalized_query}"

    def _search_cache_key(self, *, query: str, limit: int, offset: int, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:orders:v{namespace}:search:{quote_plus(query)}:{limit}:{offset}"

    def _validate_pagination(self, *, limit: int, offset: int) -> None:
        if limit <= 0 or limit > self.max_limit or offset < 0:
            raise AppError(
                status_code=400,
                code="invalid_pagination",
                message=f"Pagination must satisfy 0 < limit <= {self.max_limit} and offset >= 0",
            )

    @staticmethod
    def _normalize_description(value: str) -> str:
        normalized = sanitize_text(value, max_length=5000)
        if not normalized:
            raise AppError(status_code=400, code="invalid_description", message="Description is required")
        return normalized

    @staticmethod
    def _normalize_price(value: Decimal) -> Decimal:
        try:
            price = Decimal(value).quantize(Decimal("0.01"))
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_price", message="Invalid price") from exc
        if price <= 0:
            raise AppError(status_code=400, code="invalid_price", message="Invalid price")
        return price

    @staticmethod
    def _normalize_status(value: OrderStatus | str) -> OrderStatus:
        if isinstance(value, OrderStatus):
            return value
        try:
            return OrderStatus(str(value))
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_status", message="Invalid status") from exc

    @staticmethod
    def _order_to_payload(order: Order) -> dict[str, Any]:
        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "client_id": order.client_id,
            "description": order.description,
            "price": order.price,
            "status": order.status,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }

    @staticmethod
    def _payload_to_order(payload: dict[str, Any]) -> Order:
        return Order(
            id=payload["id"],
            tenant_id=payload["tenant_id"],
            client_id=payload["client_id"],
            description=payload["description"],
            price=payload["price"],
            status=payload["status"],
            created_at=payload["created_at"]
            if isinstance(payload["created_at"], datetime)
            else datetime.fromisoformat(str(payload["created_at"])),
            updated_at=payload["updated_at"]
            if isinstance(payload["updated_at"], datetime)
            else datetime.fromisoformat(str(payload["updated_at"])),
        )

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError, CrossTenantDataViolation
from app.core.input_security import guard_against_sqli, sanitize_text
from app.core.serialization import JsonSerializer, Serializer
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.services.audit_decorator import audit
from app.services.audit_log_service import AuditLogService
from app.services.base_service import BaseService
from app.services.idempotency_service import IdempotencyDecision, IdempotencyService


_CACHE_MISS = object()
_NAMESPACE_TTL_SECONDS = 60 * 60 * 24 * 30


class ClientService(BaseService):
    """Business service for tenant-scoped client operations."""

    def __init__(
        self,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ):
        self.actor_role = (actor_role or "").lower() if actor_role else None

        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )

        settings = get_settings()
        self.cache_ttl_seconds = settings.client_cache_ttl_seconds
        self.negative_cache_ttl_seconds = settings.negative_cache_ttl_seconds
        self.max_limit = settings.max_limit
        self.service_rate_limit_per_minute = settings.service_rate_limit_per_minute

        self.audit_service = AuditLogService(tenant_id=tenant_id, session_factory=self._session_factory)
        self.idempotency_service = IdempotencyService(self)

    @audit(action="create", entity="client")
    async def create_client(
        self,
        *,
        name: str,
        phone: str,
        email: str | None = None,
        comment: str | None = None,
        idempotency_key: str | None = None,
    ) -> Client:
        await self._enforce_service_rate_limit("clients:create")

        normalized_name = self._normalize_required_string(name, field="name", max_length=200)
        normalized_phone = self._normalize_phone(phone)
        normalized_email = self._normalize_email(email)
        normalized_comment = self._normalize_optional_string(comment, max_length=5000)

        idempotency_decision: IdempotencyDecision | None = None
        if idempotency_key and idempotency_key.strip() and self.actor_user_id is not None:
            payload_hash = self.idempotency_service.build_request_hash(
                {
                    "name": normalized_name,
                    "phone": normalized_phone,
                    "email": normalized_email,
                    "comment": normalized_comment,
                }
            )
            idempotency_decision = await self.idempotency_service.begin(
                tenant_id=self.tenant_id,
                actor_id=self.actor_user_id,
                route="POST:/clients",
                key=idempotency_key.strip()[:128],
                request_hash=payload_hash,
            )
            if not idempotency_decision.proceed:
                if not isinstance(idempotency_decision.response_payload, dict):
                    raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
                return self._payload_to_client(idempotency_decision.response_payload)

        def write_op(db: Session) -> dict[str, Any]:
            repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            client = repo.create(
                name=normalized_name,
                phone=normalized_phone,
                email=normalized_email,
                comment=normalized_comment,
            )
            return self._client_to_payload(client)

        try:
            payload = await self.execute_write(write_op, idempotent=False)
        except IntegrityError as exc:
            if idempotency_decision and idempotency_decision.record_id is not None:
                await self._safe_mark_idempotency_failed(idempotency_decision.record_id)
            if self._is_phone_unique_violation(exc):
                raise AppError(status_code=409, code="phone_already_exists", message="Phone already exists") from exc
            raise
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
        return self._payload_to_client(payload)

    @audit(action="update", entity="client")
    async def update_client(
        self,
        *,
        client_id: UUID,
        name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        comment: str | None = None,
        expected_version: int | None = None,
    ) -> Client:
        await self._enforce_service_rate_limit("clients:update")

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = self._normalize_required_string(name, field="name", max_length=200)
        if phone is not None:
            updates["phone"] = self._normalize_phone(phone)
        if email is not None:
            updates["email"] = self._normalize_email(email)
        if comment is not None:
            updates["comment"] = self._normalize_optional_string(comment, max_length=5000)

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        before_payload: dict[str, Any] | None = None

        def write_op(db: Session) -> dict[str, Any]:
            nonlocal before_payload
            repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            current_client = repo.get_by_id(client_id)
            if current_client is None:
                raise AppError(status_code=404, code="client_not_found", message="Client not found")

            if expected_version is not None and current_client.version != expected_version:
                raise AppError(status_code=409, code="concurrent_update", message="Concurrent update detected")

            before_payload = self._client_to_payload(current_client)
            updated = repo.update(client_id, **updates)
            if updated is None:
                raise AppError(status_code=404, code="client_not_found", message="Client not found")
            return self._client_to_payload(updated)

        try:
            payload = await self.execute_write(write_op, idempotent=False)
        except IntegrityError as exc:
            if self._is_phone_unique_violation(exc):
                raise AppError(status_code=409, code="phone_already_exists", message="Phone already exists") from exc
            raise
        except StaleDataError as exc:
            raise AppError(status_code=409, code="concurrent_update", message="Concurrent update detected") from exc

        if before_payload is not None:
            changed_fields = [field for field in updates if before_payload.get(field) != payload.get(field)]
            await self._log_diff(client_id=client_id, before=before_payload, after=payload, changed_fields=changed_fields)

        await self._bump_namespace_version()
        return self._payload_to_client(payload)

    @audit(action="delete", entity="client")
    async def delete_client(self, *, client_id: UUID) -> None:
        await self._enforce_service_rate_limit("clients:delete")

        def write_op(db: Session) -> bool:
            repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            return repo.soft_delete_by_id(client_id, deleted_at=datetime.now(UTC))

        deleted = await self.execute_write(write_op, idempotent=False)
        if not deleted:
            raise AppError(status_code=404, code="client_not_found", message="Client not found")

        await self._bump_namespace_version()

    async def get_client(self, *, client_id: UUID) -> Client:
        namespace = await self._get_namespace_version()
        key = self._client_cache_key(client_id=client_id, namespace=namespace)

        async def loader() -> dict[str, Any] | None:
            def read_op(db: Session) -> dict[str, Any] | None:
                repo = ClientRepository(db=db, tenant_id=self.tenant_id)
                client = repo.get_by_id(client_id)
                if client is None:
                    return None
                return self._client_to_payload(client)

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader, negative_ttl=self.negative_cache_ttl_seconds)
        if payload is None:
            raise AppError(status_code=404, code="client_not_found", message="Client not found")
        return self._payload_to_client(self._mask_payload(payload))

    async def search_clients(self, *, query: str, limit: int = 50, offset: int = 0) -> list[Client]:
        self._validate_pagination(limit=limit, offset=offset)

        search_query = guard_against_sqli(query.strip())
        if len(search_query) > 100:
            search_query = search_query[:100]
        if not search_query:
            return await self.list_clients_paginated(limit=limit, offset=offset)

        namespace = await self._get_namespace_version()
        key = self._search_cache_key(query=search_query, limit=limit, offset=offset, namespace=namespace)

        async def loader() -> list[dict[str, Any]]:
            def read_op(db: Session) -> list[dict[str, Any]]:
                repo = ClientRepository(db=db, tenant_id=self.tenant_id)
                clients = repo.search(search_query, limit=limit, offset=offset)
                return [self._client_to_payload(client) for client in clients]

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        if not isinstance(payload, list):
            return []
        return [self._payload_to_client(self._mask_payload(item)) for item in payload if isinstance(item, dict)]

    async def list_clients_paginated(self, *, limit: int, offset: int) -> list[Client]:
        self._validate_pagination(limit=limit, offset=offset)
        namespace = await self._get_namespace_version()
        key = self._list_cache_key(limit=limit, offset=offset, namespace=namespace)

        async def loader() -> list[dict[str, Any]]:
            def read_op(db: Session) -> list[dict[str, Any]]:
                repo = ClientRepository(db=db, tenant_id=self.tenant_id)
                clients = repo.paginate(limit=limit, offset=offset)
                return [self._client_to_payload(client) for client in clients]

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        if not isinstance(payload, list):
            return []
        return [self._payload_to_client(self._mask_payload(item)) for item in payload if isinstance(item, dict)]

    async def list_clients_by_ids(self, *, ids: list[UUID]) -> list[Client]:
        if not ids:
            return []

        def read_op(db: Session) -> list[dict[str, Any]]:
            repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            clients = repo.list_by_ids(ids)
            return [self._client_to_payload(client) for client in clients]

        payloads = await self.execute_read(read_op)
        return [self._payload_to_client(self._mask_payload(item)) for item in payloads if isinstance(item, dict)]

    async def count_clients(self, *, query: str | None = None) -> int:
        normalized_query = guard_against_sqli(query.strip()) if query else None
        if normalized_query and len(normalized_query) > 100:
            normalized_query = normalized_query[:100]

        namespace = await self._get_namespace_version()
        key = self._count_cache_key(query=normalized_query, namespace=namespace)

        async def loader() -> int:
            def read_op(db: Session) -> int:
                repo = ClientRepository(db=db, tenant_id=self.tenant_id)
                return int(repo.count(normalized_query))

            return await self.execute_read(read_op)

        payload = await self._cached_or_load(key=key, loader=loader)
        return int(payload)

    async def _cached_or_load(
        self,
        *,
        key: str,
        loader,
        negative_ttl: int | None = None,
    ):
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

    def _namespace_version_key(self) -> str:
        return f"tenant:{self.tenant_id}:clients:namespace"

    async def _enforce_service_rate_limit(self, operation: str) -> None:
        actor = str(self.actor_user_id) if self.actor_user_id else "anonymous"
        key = f"tenant:{self.tenant_id}:clients:svc_rl:{actor}:{operation}"
        await self.service_rate_limit(key=key, limit=self.service_rate_limit_per_minute, window_seconds=60)

    async def _safe_mark_idempotency_failed(self, record_id: UUID) -> None:
        try:
            await self.idempotency_service.mark_failed(tenant_id=self.tenant_id, record_id=record_id)
        except Exception:
            return

    async def _log_diff(
        self,
        *,
        client_id: UUID,
        before: dict[str, Any],
        after: dict[str, Any],
        changed_fields: list[str],
    ) -> None:
        if self.actor_user_id is None:
            return
        try:
            await self.audit_service.log_action(
                user_id=self.actor_user_id,
                action="update_diff",
                entity="client",
                entity_id=client_id,
                metadata={"before": before, "after": after, "changed_fields": changed_fields},
            )
        except Exception:
            return

    def _client_cache_key(self, *, client_id: UUID, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:clients:v{namespace}:get:{client_id}"

    def _list_cache_key(self, *, limit: int, offset: int, namespace: int) -> str:
        return f"tenant:{self.tenant_id}:clients:v{namespace}:list:{limit}:{offset}"

    def _count_cache_key(self, *, query: str | None, namespace: int) -> str:
        normalized_query = quote_plus(query) if query else "_all"
        return f"tenant:{self.tenant_id}:clients:v{namespace}:count:{normalized_query}"

    def _search_cache_key(self, *, query: str, limit: int, offset: int, namespace: int) -> str:
        normalized_query = quote_plus(query)
        return f"tenant:{self.tenant_id}:clients:v{namespace}:search:{normalized_query}:{limit}:{offset}"

    def _validate_pagination(self, *, limit: int, offset: int) -> None:
        if limit <= 0 or limit > self.max_limit or offset < 0:
            raise AppError(
                status_code=400,
                code="invalid_pagination",
                message=f"Pagination must satisfy 0 < limit <= {self.max_limit} and offset >= 0",
            )

    @staticmethod
    def _normalize_required_string(value: str, *, field: str, max_length: int) -> str:
        normalized = sanitize_text(value, max_length=max_length)
        if not normalized:
            raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}")
        return normalized

    @staticmethod
    def _normalize_optional_string(value: str | None, *, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = sanitize_text(value, max_length=max_length)
        return normalized if normalized else None

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        raw = phone.strip()
        if not raw:
            raise AppError(status_code=400, code="invalid_phone", message="Invalid phone")

        cleaned = re.sub(r"[^\d]", "", raw)
        if not cleaned.isdigit():
            raise AppError(status_code=400, code="invalid_phone", message="Invalid phone")
        if not 6 <= len(cleaned) <= 15:
            raise AppError(status_code=400, code="invalid_phone", message="Invalid phone")

        return cleaned

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        if email is None:
            return None
        normalized = email.strip()
        if not normalized:
            return None
        try:
            result = validate_email(normalized, check_deliverability=False)
        except EmailNotValidError as exc:
            raise AppError(status_code=400, code="invalid_email", message="Invalid email") from exc
        return result.normalized

    @staticmethod
    def _is_phone_unique_violation(exc: IntegrityError) -> bool:
        message = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
        return "uq_clients_tenant_phone" in message

    def _mask_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.actor_role != "employee":
            return payload

        masked = dict(payload)
        phone = masked.get("phone")
        email = masked.get("email")

        if isinstance(phone, str) and len(phone) >= 4:
            masked["phone"] = f"{'*' * (len(phone) - 4)}{phone[-4:]}"
        if isinstance(email, str) and "@" in email:
            local, domain = email.split("@", 1)
            safe_local = local[:2] + "***" if len(local) > 2 else "***"
            masked["email"] = f"{safe_local}@{domain}"

        return masked

    @staticmethod
    def _client_to_payload(client: Client) -> dict[str, Any]:
        return {
            "id": client.id,
            "tenant_id": client.tenant_id,
            "name": client.name,
            "phone": client.phone,
            "email": client.email,
            "comment": client.comment,
            "version": client.version,
            "created_at": client.created_at,
            "updated_at": client.updated_at,
            "deleted_at": client.deleted_at,
        }

    @staticmethod
    def _payload_to_client(payload: dict[str, Any]) -> Client:
        client_id = payload["id"] if isinstance(payload["id"], UUID) else UUID(str(payload["id"]))
        tenant_id = payload["tenant_id"] if isinstance(payload["tenant_id"], UUID) else UUID(str(payload["tenant_id"]))

        created_at_raw = payload["created_at"]
        updated_at_raw = payload["updated_at"]
        created_at = created_at_raw if isinstance(created_at_raw, datetime) else datetime.fromisoformat(str(created_at_raw))
        updated_at = updated_at_raw if isinstance(updated_at_raw, datetime) else datetime.fromisoformat(str(updated_at_raw))

        deleted_at_raw = payload.get("deleted_at")
        if deleted_at_raw is None or isinstance(deleted_at_raw, datetime):
            deleted_at = deleted_at_raw
        else:
            deleted_at = datetime.fromisoformat(str(deleted_at_raw))

        return Client(
            id=client_id,
            tenant_id=tenant_id,
            name=payload["name"],
            phone=payload["phone"],
            email=payload.get("email"),
            comment=payload.get("comment"),
            version=int(payload["version"]),
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
        )

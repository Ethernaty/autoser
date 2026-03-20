from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.http_delivery_engine import get_http_delivery_engine
from app.core.prometheus_metrics import get_metrics_registry
from app.core.serialization import JsonSerializer, Serializer
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_endpoint import WebhookEndpoint
from app.models.webhook_event import WebhookEvent
from app.repositories.webhook_delivery_repository import WebhookDeliveryRepository
from app.repositories.webhook_endpoint_repository import WebhookEndpointRepository
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.services.base_service import BaseService
from app.services.event_dispatcher_service import EventDispatcherService, JobQueueEventAdapter


@dataclass(frozen=True)
class WebhookEndpointCreateResult:
    endpoint: WebhookEndpoint
    signing_secret: str


@dataclass(frozen=True)
class DeliveryExecutionContext:
    delivery: WebhookDelivery
    endpoint: WebhookEndpoint
    event: WebhookEvent
    payload_bytes: bytes
    signature: str


class WebhookService(BaseService):
    """Webhook endpoint management and delivery execution engine."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self._settings = get_settings()
        self._metrics = get_metrics_registry()
        self._http_delivery_engine = get_http_delivery_engine()
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )
        self._dispatcher = EventDispatcherService(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
            adapter=JobQueueEventAdapter(),
        )

    async def create_endpoint(
        self,
        *,
        url: str,
        description: str | None,
        events: list[str],
    ) -> WebhookEndpointCreateResult:
        self._assert_manageable_role()

        normalized_url = self._normalize_url(url)
        normalized_events = self._normalize_events(events)
        normalized_description = description.strip()[:200] if description else None
        signing_secret = self._generate_signing_secret()

        def write_op(db: Session) -> WebhookEndpoint:
            repo = WebhookEndpointRepository(db=db, tenant_id=self.tenant_id)
            return repo.create(
                url=normalized_url,
                description=normalized_description,
                secret=signing_secret,
                events=normalized_events,
                is_active=True,
            )

        endpoint = await self.execute_write(write_op, idempotent=False)
        return WebhookEndpointCreateResult(endpoint=endpoint, signing_secret=signing_secret)

    async def list_endpoints(self) -> list[WebhookEndpoint]:
        self._assert_manageable_role()

        def read_op(db: Session) -> list[WebhookEndpoint]:
            repo = WebhookEndpointRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_all()

        return await self.execute_read(read_op)

    async def deactivate_endpoint(self, *, endpoint_id: UUID) -> None:
        self._assert_manageable_role()

        def write_op(db: Session) -> bool:
            repo = WebhookEndpointRepository(db=db, tenant_id=self.tenant_id)
            return repo.deactivate(endpoint_id)

        success = await self.execute_write(write_op, idempotent=True)
        if not success:
            raise AppError(status_code=404, code="webhook_endpoint_not_found", message="Webhook endpoint not found")

    async def list_deliveries(self, *, limit: int, offset: int, status: str | None = None) -> list[WebhookDelivery]:
        self._assert_manageable_role()

        normalized_status = status.strip().lower() if status else None

        def read_op(db: Session) -> list[WebhookDelivery]:
            repo = WebhookDeliveryRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_paginated(limit=limit, offset=offset, status=normalized_status)

        return await self.execute_read(read_op)

    async def publish_event(self, *, event_name: str, payload: dict[str, Any]) -> UUID:
        self._assert_manageable_role()
        published = await self._dispatcher.publish_event(event_name=event_name, payload=payload)
        return published.event_id

    async def process_delivery(self, *, delivery_id: UUID) -> None:
        execution_context = await self._load_execution_context(delivery_id=delivery_id)
        if execution_context is None:
            return

        response_code, response_body, error_message = await self._send_signed_request(
            url=execution_context.endpoint.url,
            payload=execution_context.payload_bytes,
            signature=execution_context.signature,
        )

        now = datetime.now(UTC)
        attempt = int(execution_context.delivery.attempt) + 1
        max_attempts = int(execution_context.delivery.max_attempts)

        if error_message is None and response_code is not None and 200 <= response_code < 300:
            await self._mark_delivery_success(
                delivery_id=execution_context.delivery.id,
                response_code=response_code,
                response_body=response_body,
                delivered_at=now,
            )
            self._metrics.increment_counter("webhook_deliveries_total", labels={"status": "success"})
            return

        if attempt >= max_attempts:
            await self._mark_delivery_failure(
                delivery_id=execution_context.delivery.id,
                attempt=attempt,
                status="dead_letter",
                error=error_message or f"http_{response_code or 'error'}",
                response_code=response_code,
                response_body=response_body,
                next_retry_at=None,
            )
            self._metrics.increment_counter("webhook_deliveries_total", labels={"status": "dead_letter"})
            self._metrics.increment_counter("webhook_failures_total", labels={"reason": "dead_letter"})
            return

        backoff_seconds = self._settings.webhook_retry_base_seconds * (2 ** max(attempt - 1, 0))
        next_retry_at = now + timedelta(seconds=backoff_seconds)
        await self._mark_delivery_failure(
            delivery_id=execution_context.delivery.id,
            attempt=attempt,
            status="failed",
            error=error_message or f"http_{response_code or 'error'}",
            response_code=response_code,
            response_body=response_body,
            next_retry_at=next_retry_at,
        )
        self._metrics.increment_counter("webhook_deliveries_total", labels={"status": "retry_scheduled"})
        self._metrics.increment_counter("webhook_failures_total", labels={"reason": "retry"})

        adapter = JobQueueEventAdapter()
        await adapter.enqueue_webhook_delivery(
            tenant_id=self.tenant_id,
            delivery_id=execution_context.delivery.id,
            delay_seconds=backoff_seconds,
        )

    async def _load_execution_context(self, *, delivery_id: UUID) -> DeliveryExecutionContext | None:
        def read_op(db: Session) -> DeliveryExecutionContext | None:
            delivery_repo = WebhookDeliveryRepository(db=db, tenant_id=self.tenant_id)
            endpoint_repo = WebhookEndpointRepository(db=db, tenant_id=self.tenant_id)
            event_repo = WebhookEventRepository(db=db, tenant_id=self.tenant_id)

            delivery = delivery_repo.get_by_id(delivery_id)
            if delivery is None:
                return None
            if delivery.status in {"success", "dead_letter"}:
                return None

            endpoint = endpoint_repo.get_by_id(delivery.endpoint_id)
            event = event_repo.get_by_id(delivery.event_id)
            if endpoint is None or event is None:
                return None
            if not endpoint.is_active:
                return None

            body = json.dumps(
                {
                    "id": str(event.id),
                    "tenant_id": str(event.tenant_id),
                    "event": event.event_name,
                    "payload": event.payload,
                    "published_at": event.published_at.isoformat(),
                },
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
            signature = self._build_signature(secret=endpoint.secret, payload=body)
            return DeliveryExecutionContext(
                delivery=delivery,
                endpoint=endpoint,
                event=event,
                payload_bytes=body,
                signature=signature,
            )

        return await self.execute_read(read_op)

    async def _mark_delivery_success(
        self,
        *,
        delivery_id: UUID,
        response_code: int | None,
        response_body: str | None,
        delivered_at: datetime,
    ) -> None:
        def write_op(db: Session) -> None:
            repo = WebhookDeliveryRepository(db=db, tenant_id=self.tenant_id)
            repo.mark_success(
                delivery_id=delivery_id,
                response_code=response_code,
                response_body=response_body,
                delivered_at=delivered_at,
            )

        await self.execute_write(write_op, idempotent=False)

    async def _mark_delivery_failure(
        self,
        *,
        delivery_id: UUID,
        attempt: int,
        status: str,
        error: str,
        response_code: int | None,
        response_body: str | None,
        next_retry_at: datetime | None,
    ) -> None:
        def write_op(db: Session) -> None:
            repo = WebhookDeliveryRepository(db=db, tenant_id=self.tenant_id)
            repo.mark_failed(
                delivery_id=delivery_id,
                attempt=attempt,
                status=status,
                error=error[:1000],
                response_code=response_code,
                response_body=response_body[:4000] if response_body else None,
                next_retry_at=next_retry_at,
            )

        await self.execute_write(write_op, idempotent=False)

    async def _send_signed_request(
        self,
        *,
        url: str,
        payload: bytes,
        signature: str,
    ) -> tuple[int | None, str | None, str | None]:
        result = await self._http_delivery_engine.deliver(
            url=url,
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Signature-Alg": "hmac-sha256",
            },
            method="POST",
        )
        return result.status_code, result.body, result.error

    @staticmethod
    def _build_signature(*, secret: str, payload: bytes) -> str:
        digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return digest

    @staticmethod
    def _normalize_url(value: str) -> str:
        normalized = value.strip()
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL must be http(s)")
        if len(normalized) > 2000:
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL is too long")
        parsed = urlparse(normalized)
        if not parsed.hostname:
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL host is required")
        if parsed.username or parsed.password:
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL must not contain credentials")

        hostname = parsed.hostname.strip().lower()
        if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".localhost"):
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL host is not allowed")

        try:
            WebhookService._assert_public_host(hostname)
        except AppError:
            raise
        except Exception:
            raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL host validation failed")
        return normalized

    @staticmethod
    def _assert_public_host(hostname: str) -> None:
        try:
            ip = ipaddress.ip_address(hostname)
            if WebhookService._is_private_ip(ip):
                raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL host is not allowed")
            return
        except ValueError:
            pass

        infos = socket.getaddrinfo(hostname, None)
        for _family, _type, _proto, _canon, sockaddr in infos:
            if not sockaddr:
                continue
            address = sockaddr[0]
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            if WebhookService._is_private_ip(ip):
                raise AppError(status_code=400, code="invalid_webhook_url", message="Webhook URL host is not allowed")

    @staticmethod
    def _is_private_ip(ip: ipaddress._BaseAddress) -> bool:
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )

    @staticmethod
    def _normalize_events(events: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in events:
            value = str(item).strip().lower()
            if not value:
                continue
            normalized.append(value)
        deduped = sorted(set(normalized))
        if not deduped:
            raise AppError(status_code=400, code="invalid_webhook_events", message="At least one event is required")
        return deduped

    @staticmethod
    def _generate_signing_secret() -> str:
        return secrets.token_hex(32)

    def _assert_manageable_role(self) -> None:
        if self.actor_role in {"owner", "admin"}:
            return
        raise AppError(status_code=403, code="permission_denied", message="Permission denied")

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.database import SessionLocal
from app.core.event_stream import EventStreamBackend, get_event_stream_backend
from app.core.jobs import get_job_queue
from app.core.serialization import JsonSerializer, Serializer
from app.repositories.webhook_delivery_repository import WebhookDeliveryRepository
from app.repositories.webhook_endpoint_repository import WebhookEndpointRepository
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.services.base_service import BaseService


@dataclass(frozen=True)
class PublishedEvent:
    event_id: UUID
    tenant_id: UUID
    delivery_ids: list[UUID]


class ExternalEventAdapter(Protocol):
    async def enqueue_webhook_delivery(self, *, tenant_id: UUID, delivery_id: UUID, delay_seconds: float = 0.0) -> None:
        ...


class JobQueueEventAdapter:
    """Default adapter backed by the internal job queue."""

    async def enqueue_webhook_delivery(self, *, tenant_id: UUID, delivery_id: UUID, delay_seconds: float = 0.0) -> None:
        queue = get_job_queue()
        await queue.enqueue(
            task_name="webhook.delivery",
            payload={"tenant_id": str(tenant_id), "delivery_id": str(delivery_id)},
            delay_seconds=max(0.0, delay_seconds),
            max_retries=0,
            retry_base_delay_seconds=1.0,
        )


class EventDispatcherService(BaseService):
    """Central publish pipeline for external events and webhook jobs."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
        adapter: ExternalEventAdapter | None = None,
        event_stream: EventStreamBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )
        self._adapter = adapter or JobQueueEventAdapter()
        self._event_stream = event_stream or get_event_stream_backend()

    async def publish_event(self, *, event_name: str, payload: dict[str, Any]) -> PublishedEvent:
        normalized_name = event_name.strip().lower()
        if not normalized_name:
            from app.core.exceptions import AppError

            raise AppError(status_code=400, code="invalid_event_name", message="Event name is required")

        event_payload = dict(payload)

        def write_op(db: Session) -> PublishedEvent:
            endpoint_repo = WebhookEndpointRepository(db=db, tenant_id=self.tenant_id)
            event_repo = WebhookEventRepository(db=db, tenant_id=self.tenant_id)
            delivery_repo = WebhookDeliveryRepository(db=db, tenant_id=self.tenant_id)

            event = event_repo.create_event(event_name=normalized_name, payload=event_payload)
            endpoints = endpoint_repo.list_active()
            delivery_ids: list[UUID] = []

            for endpoint in endpoints:
                if not self._endpoint_allows_event(endpoint.events, normalized_name):
                    continue
                delivery = delivery_repo.create_delivery(
                    endpoint_id=endpoint.id,
                    event_id=event.id,
                    max_attempts=self._settings.webhook_max_attempts,
                )
                delivery_ids.append(delivery.id)

            return PublishedEvent(
                event_id=event.id,
                tenant_id=self.tenant_id,
                delivery_ids=delivery_ids,
            )

        published = await self.execute_write(write_op, idempotent=False)
        for delivery_id in published.delivery_ids:
            try:
                await self._adapter.enqueue_webhook_delivery(
                    tenant_id=self.tenant_id,
                    delivery_id=delivery_id,
                    delay_seconds=0.0,
                )
            except Exception:
                continue
        try:
            await self._event_stream.publish(
                tenant_id=self.tenant_id,
                name=normalized_name,
                payload=event_payload,
            )
        except Exception:
            pass
        return published

    @staticmethod
    def _endpoint_allows_event(allowed_events: list[str], event_name: str) -> bool:
        normalized = {str(item).strip().lower() for item in allowed_events if str(item).strip()}
        return "*" in normalized or event_name in normalized

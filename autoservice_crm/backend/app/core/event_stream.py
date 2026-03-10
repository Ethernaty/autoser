from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.prometheus_metrics import get_metrics_registry
from app.core.reliability.chaos import get_chaos_engine
from app.core.serialization import JsonSerializer, Serializer


@dataclass(frozen=True)
class EventMessage:
    event_id: UUID
    tenant_id: UUID
    name: str
    payload: dict[str, Any]
    created_at: datetime


class EventStreamBackend(Protocol):
    async def publish(self, *, tenant_id: UUID, name: str, payload: dict[str, Any]) -> EventMessage:
        ...

    async def replay(self, *, tenant_id: UUID, limit: int = 100) -> list[EventMessage]:
        ...

    async def close(self) -> None:
        ...


class MemoryEventStreamAdapter:
    """In-process event stream fallback."""

    def __init__(self) -> None:
        self._messages: list[EventMessage] = []
        self._lock = asyncio.Lock()
        self._metrics = get_metrics_registry()
        self._chaos = get_chaos_engine()

    async def publish(self, *, tenant_id: UUID, name: str, payload: dict[str, Any]) -> EventMessage:
        message = EventMessage(
            event_id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            payload=dict(payload),
            created_at=datetime.now(UTC),
        )
        if self._chaos.should_drop_event():
            self._metrics.increment_counter("event_stream_dropped_total", labels={"backend": "memory"})
            return message
        async with self._lock:
            self._messages.append(message)
        return message

    async def replay(self, *, tenant_id: UUID, limit: int = 100) -> list[EventMessage]:
        cap = max(1, min(1000, limit))
        async with self._lock:
            filtered = [item for item in self._messages if item.tenant_id == tenant_id]
            return list(filtered[-cap:])

    async def close(self) -> None:
        async with self._lock:
            self._messages.clear()


class KafkaEventStreamAdapter:
    """Kafka-backed event stream with tenant partition key and replay support."""

    def __init__(self, *, bootstrap_servers: str, topic: str, group_id: str, serializer: Serializer | None = None) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._serializer = serializer or JsonSerializer()
        self._producer = None
        self._metrics = get_metrics_registry()
        self._chaos = get_chaos_engine()

    async def _get_producer(self):
        if self._producer is not None:
            return self._producer
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            linger_ms=5,
            enable_idempotence=True,
        )
        await producer.start()
        self._producer = producer
        return producer

    async def publish(self, *, tenant_id: UUID, name: str, payload: dict[str, Any]) -> EventMessage:
        message = EventMessage(
            event_id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            payload=dict(payload),
            created_at=datetime.now(UTC),
        )
        if self._chaos.should_drop_event():
            self._metrics.increment_counter("event_stream_dropped_total", labels={"backend": "kafka"})
            return message
        producer = await self._get_producer()
        wire_payload = {
            "event_id": str(message.event_id),
            "tenant_id": str(message.tenant_id),
            "name": message.name,
            "payload": message.payload,
            "created_at": message.created_at.isoformat(),
        }
        await producer.send_and_wait(
            self._topic,
            key=str(tenant_id).encode("utf-8"),
            value=json.dumps(wire_payload, separators=(",", ":"), default=str).encode("utf-8"),
        )
        self._metrics.increment_counter("event_stream_published_total", labels={"backend": "kafka"})
        return message

    async def replay(self, *, tenant_id: UUID, limit: int = 100) -> list[EventMessage]:
        from aiokafka import AIOKafkaConsumer, TopicPartition

        cap = max(1, min(1000, limit))
        consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=f"{self._group_id}.replay",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await consumer.start()
        result: list[EventMessage] = []
        try:
            partitions = await consumer.partitions_for_topic(self._topic)
            if not partitions:
                return []

            topic_partitions = [TopicPartition(self._topic, partition) for partition in sorted(partitions)]
            await consumer.assign(topic_partitions)
            end_offsets = await consumer.end_offsets(topic_partitions)

            for tp in topic_partitions:
                await consumer.seek(tp, 0)

            while len(result) < cap:
                batch = await consumer.getmany(timeout_ms=250, max_records=500)
                if not batch:
                    break
                for records in batch.values():
                    for record in records:
                        item = self._decode_message(record.value)
                        if item is None or item.tenant_id != tenant_id:
                            continue
                        result.append(item)
                        if len(result) >= cap:
                            break
                    if len(result) >= cap:
                        break

                reached_end = True
                for tp in topic_partitions:
                    position = await consumer.position(tp)
                    if position < end_offsets.get(tp, 0):
                        reached_end = False
                        break
                if reached_end:
                    break
        finally:
            await consumer.stop()
        return result[-cap:]

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    def _decode_message(self, payload: bytes | bytearray | memoryview | None) -> EventMessage | None:
        if payload is None:
            return None
        try:
            parsed = json.loads(bytes(payload).decode("utf-8"))
            return EventMessage(
                event_id=UUID(str(parsed["event_id"])),
                tenant_id=UUID(str(parsed["tenant_id"])),
                name=str(parsed["name"]),
                payload=dict(parsed.get("payload") or {}),
                created_at=datetime.fromisoformat(str(parsed["created_at"])),
            )
        except Exception:
            return None


@lru_cache(maxsize=1)
def get_event_stream_backend() -> EventStreamBackend:
    settings = get_settings()
    if settings.event_stream_backend == "kafka":
        try:
            return KafkaEventStreamAdapter(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                topic=settings.kafka_event_topic,
                group_id=settings.job_queue_consumer_group,
            )
        except Exception:
            return MemoryEventStreamAdapter()
    return MemoryEventStreamAdapter()

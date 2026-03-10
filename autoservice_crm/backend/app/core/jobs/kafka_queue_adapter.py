from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from app.core.jobs.job_queue import JobEnvelope, JobQueue
from app.core.prometheus_metrics import get_metrics_registry


@dataclass(frozen=True)
class _KafkaDeliveryTag:
    topic: str
    partition: int
    offset: int

    @property
    def encoded(self) -> str:
        return f"{self.topic}:{self.partition}:{self.offset}"

    @classmethod
    def decode(cls, value: str) -> "_KafkaDeliveryTag":
        topic, partition, offset = value.split(":")
        return cls(topic=topic, partition=int(partition), offset=int(offset))


class KafkaQueueAdapter(JobQueue):
    """Kafka queue adapter with manual commits and dead-letter support."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        dead_letter_topic: str,
        consumer_group: str,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._dead_letter_topic = dead_letter_topic
        self._consumer_group = consumer_group
        self._producer = None
        self._consumer = None
        self._assignment_ready = False
        self._metrics = get_metrics_registry()
        self._inflight: dict[str, _KafkaDeliveryTag] = {}
        self._inflight_lock = asyncio.Lock()

    async def enqueue(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        max_retries: int = 3,
        retry_base_delay_seconds: float = 1.0,
        delay_seconds: float = 0.0,
    ) -> JobEnvelope:
        envelope = JobEnvelope(
            available_at=time.time() + max(0.0, delay_seconds),
            task_name=task_name,
            payload=dict(payload),
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            backend="kafka",
        )
        producer = await self._get_producer()
        await producer.send_and_wait(
            self._topic,
            key=task_name.encode("utf-8"),
            value=self._encode_job(envelope),
        )
        return envelope

    async def dequeue(self, timeout_seconds: float = 1.0) -> JobEnvelope | None:
        consumer = await self._get_consumer()
        records = await consumer.getmany(timeout_ms=max(50, int(timeout_seconds * 1000)), max_records=1)
        if not records:
            return None

        for tp, batch in records.items():
            if not batch:
                continue
            record = batch[0]
            envelope = self._decode_job(record.value)
            if envelope is None:
                await consumer.commit({tp: record.offset + 1})
                continue

            now = time.time()
            if envelope.available_at > now:
                wait_seconds = max(0.05, min(1.0, envelope.available_at - now))
                await asyncio.sleep(wait_seconds)
                if envelope.attempts > envelope.max_retries:
                    await self._send_to_dead_letter(envelope)
                else:
                    await self._republish(envelope)
                await consumer.commit({tp: record.offset + 1})
                continue

            delivery_tag = _KafkaDeliveryTag(topic=tp.topic, partition=tp.partition, offset=record.offset)
            envelope.delivery_tag = delivery_tag.encoded
            envelope.delivery_token = uuid4().hex

            async with self._inflight_lock:
                self._inflight[str(envelope.id)] = delivery_tag
            queue_delay = max(0.0, time.time() - float(envelope.created_at))
            self._metrics.observe_histogram("job_queue_delay_seconds", queue_delay, labels={"backend": "kafka"})
            return envelope
        return None

    async def requeue(self, job: JobEnvelope, *, error: Exception) -> None:
        if job.delivery_tag is None:
            return

        job.attempts += 1
        job.last_error = str(error)
        if job.attempts > job.max_retries:
            await self._send_to_dead_letter(job)
            await self.ack(job)
            return

        backoff = job.retry_base_delay_seconds * (2 ** max(job.attempts - 1, 0))
        job.available_at = time.time() + backoff
        await self._republish(job)
        await self.ack(job)

    async def ack(self, job: JobEnvelope) -> None:
        if job.delivery_tag is None:
            return
        tag = _KafkaDeliveryTag.decode(job.delivery_tag)
        consumer = await self._get_consumer()
        from aiokafka import TopicPartition

        tp = TopicPartition(tag.topic, tag.partition)
        await consumer.commit({tp: tag.offset + 1})
        async with self._inflight_lock:
            self._inflight.pop(str(job.id), None)

    async def size(self) -> int:
        # Kafka queue depth is broker-side metric; return inflight approximation.
        async with self._inflight_lock:
            return len(self._inflight)

    async def ping(self) -> bool:
        try:
            producer = await self._get_producer()
            await producer.partitions_for(self._topic)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        async with self._inflight_lock:
            self._inflight.clear()

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

    async def _get_consumer(self):
        if self._consumer is not None:
            return self._consumer
        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
        )
        await consumer.start()
        self._consumer = consumer
        return consumer

    def _encode_job(self, job: JobEnvelope) -> bytes:
        payload = {
            "id": str(job.id),
            "task_name": job.task_name,
            "payload": job.payload,
            "attempts": job.attempts,
            "max_retries": job.max_retries,
            "retry_base_delay_seconds": job.retry_base_delay_seconds,
            "created_at": job.created_at,
            "available_at": job.available_at,
            "last_error": job.last_error,
        }
        return json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")

    def _decode_job(self, raw: bytes) -> JobEnvelope | None:
        try:
            parsed = json.loads(raw.decode("utf-8"))
            return JobEnvelope(
                id=UUID(str(parsed["id"])),
                task_name=str(parsed["task_name"]),
                payload=dict(parsed.get("payload") or {}),
                attempts=int(parsed.get("attempts") or 0),
                max_retries=int(parsed.get("max_retries") or 3),
                retry_base_delay_seconds=float(parsed.get("retry_base_delay_seconds") or 1.0),
                created_at=float(parsed.get("created_at") or time.time()),
                available_at=float(parsed.get("available_at") or time.time()),
                last_error=(parsed.get("last_error") or None),
                backend="kafka",
            )
        except Exception:
            return None

    async def _republish(self, job: JobEnvelope) -> None:
        producer = await self._get_producer()
        await producer.send_and_wait(
            self._topic,
            key=job.task_name.encode("utf-8"),
            value=self._encode_job(job),
        )
        self._metrics.increment_counter("job_queue_requeued_total", labels={"backend": "kafka"})

    async def _send_to_dead_letter(self, job: JobEnvelope) -> None:
        producer = await self._get_producer()
        payload = {
            "id": str(job.id),
            "task_name": job.task_name,
            "payload": job.payload,
            "attempts": job.attempts,
            "max_retries": job.max_retries,
            "last_error": job.last_error,
            "created_at": job.created_at,
        }
        await producer.send_and_wait(
            self._dead_letter_topic,
            key=job.task_name.encode("utf-8"),
            value=json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"),
        )
        self._metrics.increment_counter("job_queue_dead_letter_total", labels={"backend": "kafka"})

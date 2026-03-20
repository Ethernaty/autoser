from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.core.prometheus_metrics import get_metrics_registry
from app.core.reliability.chaos import get_chaos_engine


@dataclass(order=True)
class JobEnvelope:
    available_at: float
    id: UUID = field(default_factory=uuid4, compare=False)
    task_name: str = field(default="", compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)
    attempts: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    retry_base_delay_seconds: float = field(default=1.0, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    last_error: str | None = field(default=None, compare=False)
    delivery_token: str | None = field(default=None, compare=False)
    delivery_tag: str | None = field(default=None, compare=False)
    backend: str = field(default="memory", compare=False)


class JobQueue(Protocol):
    async def enqueue(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        max_retries: int = 3,
        retry_base_delay_seconds: float = 1.0,
        delay_seconds: float = 0.0,
    ) -> JobEnvelope:
        ...

    async def dequeue(self, timeout_seconds: float = 1.0) -> JobEnvelope | None:
        ...

    async def requeue(self, job: JobEnvelope, *, error: Exception) -> None:
        ...

    async def ack(self, job: JobEnvelope) -> None:
        ...

    async def size(self) -> int:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...


class InMemoryJobQueue(JobQueue):
    """Async in-memory queue with scheduled retry support."""

    def __init__(self):
        self._heap: list[JobEnvelope] = []
        self._lock = asyncio.Lock()
        self._chaos = get_chaos_engine()
        self._metrics = get_metrics_registry()

    async def enqueue(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        max_retries: int = 3,
        retry_base_delay_seconds: float = 1.0,
        delay_seconds: float = 0.0,
    ) -> JobEnvelope:
        await self._chaos.maybe_add_queue_delay_async()
        job = JobEnvelope(
            available_at=time.monotonic() + max(0.0, delay_seconds),
            task_name=task_name,
            payload=payload,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            backend="memory",
        )
        async with self._lock:
            heapq.heappush(self._heap, job)
        return job

    async def dequeue(self, timeout_seconds: float = 1.0) -> JobEnvelope | None:
        await self._chaos.maybe_add_queue_delay_async()
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() <= deadline:
            async with self._lock:
                if self._heap:
                    current = self._heap[0]
                    now = time.monotonic()
                    if current.available_at <= now:
                        job = heapq.heappop(self._heap)
                        queue_delay = max(0.0, time.time() - float(job.created_at))
                        self._metrics.observe_histogram("job_queue_delay_seconds", queue_delay, labels={"backend": "memory"})
                        return job
            await asyncio.sleep(0.05)
        return None

    async def requeue(self, job: JobEnvelope, *, error: Exception) -> None:
        job.attempts += 1
        job.last_error = str(error)
        backoff = job.retry_base_delay_seconds * (2 ** max(job.attempts - 1, 0))
        job.available_at = time.monotonic() + backoff
        async with self._lock:
            heapq.heappush(self._heap, job)

    async def ack(self, job: JobEnvelope) -> None:
        return None

    async def size(self) -> int:
        async with self._lock:
            return len(self._heap)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        async with self._lock:
            self._heap.clear()

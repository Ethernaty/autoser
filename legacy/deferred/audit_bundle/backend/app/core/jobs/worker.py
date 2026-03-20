from __future__ import annotations

import asyncio
import logging
from inspect import iscoroutinefunction
from typing import Any

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.jobs.job_queue import InMemoryJobQueue, JobEnvelope, JobQueue
from app.core.jobs.task_registry import TaskDefinition, TaskRegistry, default_task_registry
from app.core.prometheus_metrics import get_metrics_registry


class JobWorker:
    """Async worker for in-process queue execution."""

    def __init__(
        self,
        queue: JobQueue,
        registry: TaskRegistry,
        *,
        poll_timeout_seconds: float = 1.0,
        cache_backend: CacheBackend | None = None,
        logger: logging.Logger | None = None,
    ):
        self.queue = queue
        self.registry = registry
        self.poll_timeout_seconds = poll_timeout_seconds
        self.logger = logger or logging.getLogger("app.jobs.worker")
        self._cache = cache_backend or get_cache_backend()
        self._settings = get_settings()
        self._metrics = get_metrics_registry()
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            job = await self.queue.dequeue(timeout_seconds=self.poll_timeout_seconds)
            if job is None:
                continue
            await self._execute(job)

    async def _execute(self, job: JobEnvelope) -> None:
        definition = self.registry.get(job.task_name)
        if definition is None:
            self.logger.error(
                "job_task_missing",
                extra={"task_name": job.task_name, "job_id": str(job.id)},
            )
            await self.queue.ack(job)
            return

        idempotency_key = f"jobs:exec:{job.id}"
        idempotency_ttl = max(
            60,
            self._settings.job_queue_visibility_timeout_seconds * max(1, job.max_retries + 1),
        )
        try:
            reserved = await self._cache.set_if_absent(
                idempotency_key,
                {"status": "processing"},
                idempotency_ttl,
            )
        except Exception:
            reserved = True

        if not reserved:
            existing: dict[str, Any] | None = None
            try:
                value = await self._cache.get(idempotency_key)
                if isinstance(value, dict):
                    existing = value
            except Exception:
                existing = None

            if existing and existing.get("status") == "done":
                await self.queue.ack(job)
                self._metrics.increment_counter("job_queue_deduplicated_total", labels={"action": "ack_done"})
                return

            await self.queue.requeue(job, error=RuntimeError("duplicate_inflight"))
            self._metrics.increment_counter("job_queue_deduplicated_total", labels={"action": "requeue_inflight"})
            return

        try:
            await _run_task(definition, payload=job.payload)
            try:
                await self._cache.set(idempotency_key, {"status": "done"}, idempotency_ttl)
            except Exception:
                pass
            await self.queue.ack(job)
        except Exception as exc:
            if job.attempts < job.max_retries:
                await self.queue.requeue(job, error=exc)
                self.logger.warning(
                    "job_retry_scheduled",
                    extra={
                        "task_name": job.task_name,
                        "job_id": str(job.id),
                        "attempt": job.attempts,
                        "max_retries": job.max_retries,
                        "error": str(exc),
                    },
                )
                return
            self.logger.error(
                "job_failed",
                extra={
                    "task_name": job.task_name,
                    "job_id": str(job.id),
                    "attempt": job.attempts,
                    "max_retries": job.max_retries,
                    "error": str(exc),
                },
            )
            await self.queue.ack(job)


async def _run_task(definition: TaskDefinition, *, payload: dict[str, Any]) -> None:
    func = definition.func
    if iscoroutinefunction(func):
        await func(**payload)
        return
    await asyncio.to_thread(func, **payload)


settings = get_settings()
default_job_queue = InMemoryJobQueue()
default_worker = JobWorker(
    queue=default_job_queue,
    registry=default_task_registry,
    poll_timeout_seconds=settings.job_queue_poll_timeout_seconds,
)

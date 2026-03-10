from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID, uuid4

from app.core.jobs.job_queue import JobEnvelope, JobQueue
from app.core.prometheus_metrics import get_metrics_registry
from app.core.reliability.chaos import get_chaos_engine


class RedisQueueAdapter(JobQueue):
    """Redis-backed distributed queue with visibility timeout and DLQ."""

    _RELEASE_SCRIPT = """
if redis.call('GET', KEYS[2]) ~= ARGV[1] then
  return 0
end
redis.call('DEL', KEYS[2])
redis.call('LREM', KEYS[1], 1, ARGV[2])
if ARGV[3] == '1' then
  redis.call('DEL', KEYS[3])
end
return 1
""".strip()

    def __init__(
        self,
        *,
        redis_url: str,
        namespace: str,
        visibility_timeout_seconds: int,
    ) -> None:
        from redis.asyncio import Redis

        self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._namespace = namespace
        self._visibility_timeout_seconds = max(5, visibility_timeout_seconds)
        self._metrics = get_metrics_registry()
        self._chaos = get_chaos_engine()

    @property
    def _ready_key(self) -> str:
        return f"{self._namespace}:ready"

    @property
    def _processing_key(self) -> str:
        return f"{self._namespace}:processing"

    @property
    def _delayed_key(self) -> str:
        return f"{self._namespace}:delayed"

    @property
    def _dead_key(self) -> str:
        return f"{self._namespace}:dead"

    def _job_key(self, job_id: str) -> str:
        return f"{self._namespace}:job:{job_id}"

    def _lease_key(self, job_id: str) -> str:
        return f"{self._namespace}:lease:{job_id}"

    async def enqueue(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        max_retries: int = 3,
        retry_base_delay_seconds: float = 1.0,
        delay_seconds: float = 0.0,
    ) -> JobEnvelope:
        self._chaos.maybe_raise_redis_failure()
        await self._chaos.maybe_add_queue_delay_async()
        now = time.time()
        available_at = now + max(0.0, delay_seconds)
        job = JobEnvelope(
            available_at=available_at,
            task_name=task_name,
            payload=dict(payload),
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            backend="redis",
        )

        await self._redis.hset(
            self._job_key(str(job.id)),
            mapping={
                "task_name": job.task_name,
                "payload": json.dumps(job.payload, separators=(",", ":"), default=str),
                "attempts": str(job.attempts),
                "max_retries": str(job.max_retries),
                "retry_base_delay_seconds": str(job.retry_base_delay_seconds),
                "created_at": str(job.created_at),
                "available_at": str(job.available_at),
                "last_error": "",
            },
        )
        if delay_seconds > 0:
            await self._redis.zadd(self._delayed_key, {str(job.id): available_at})
        else:
            await self._redis.lpush(self._ready_key, str(job.id))
        return job

    async def dequeue(self, timeout_seconds: float = 1.0) -> JobEnvelope | None:
        self._chaos.maybe_raise_redis_failure()
        await self._chaos.maybe_add_queue_delay_async()
        await self._promote_due_jobs()
        await self._reclaim_expired_leases(limit=200)

        timeout = max(1, int(timeout_seconds))
        if hasattr(self._redis, "blmove"):
            raw_job_id = await self._redis.blmove(
                self._ready_key,
                self._processing_key,
                timeout=timeout,
                src="RIGHT",
                dest="LEFT",
            )
        else:
            raw_job_id = await self._redis.brpoplpush(self._ready_key, self._processing_key, timeout=timeout)
        if raw_job_id is None:
            return None

        job_id = str(raw_job_id)
        lease_token = uuid4().hex
        lease_key = self._lease_key(job_id)
        lease_ok = await self._redis.set(
            lease_key,
            lease_token,
            ex=self._visibility_timeout_seconds,
            nx=False,
        )
        if lease_ok is None:
            await self._redis.lrem(self._processing_key, 1, job_id)
            await self._redis.lpush(self._ready_key, job_id)
            return None

        job_data = await self._redis.hgetall(self._job_key(job_id))
        if not job_data:
            await self._release_processing(job_id=job_id, lease_token=lease_token, delete_job=True)
            return None

        envelope = self._deserialize_job(job_id=job_id, job_data=job_data, lease_token=lease_token)
        now = time.time()
        if envelope.available_at > now:
            await self._release_processing(job_id=job_id, lease_token=lease_token, delete_job=False)
            await self._redis.zadd(self._delayed_key, {job_id: envelope.available_at})
            return None
        queue_delay = max(0.0, time.time() - float(envelope.created_at))
        self._metrics.observe_histogram("job_queue_delay_seconds", queue_delay, labels={"backend": "redis"})
        return envelope

    async def requeue(self, job: JobEnvelope, *, error: Exception) -> None:
        self._chaos.maybe_raise_redis_failure()
        await self._chaos.maybe_add_queue_delay_async()
        if job.delivery_tag is None or job.delivery_token is None:
            return

        job_id = job.delivery_tag
        job.attempts += 1
        job.last_error = str(error)

        if job.attempts > job.max_retries:
            await self._send_to_dead_letter(job)
            await self._release_processing(job_id=job_id, lease_token=job.delivery_token, delete_job=True)
            return

        backoff = float(job.retry_base_delay_seconds) * (2 ** max(job.attempts - 1, 0))
        next_available = time.time() + backoff
        await self._redis.hset(
            self._job_key(job_id),
            mapping={
                "attempts": str(job.attempts),
                "last_error": str(job.last_error or "")[:1000],
                "available_at": str(next_available),
            },
        )

        released = await self._release_processing(job_id=job_id, lease_token=job.delivery_token, delete_job=False)
        if not released:
            return
        await self._redis.zadd(self._delayed_key, {job_id: next_available})

    async def ack(self, job: JobEnvelope) -> None:
        self._chaos.maybe_raise_redis_failure()
        if job.delivery_tag is None or job.delivery_token is None:
            return
        await self._release_processing(job_id=job.delivery_tag, lease_token=job.delivery_token, delete_job=True)

    async def size(self) -> int:
        self._chaos.maybe_raise_redis_failure()
        async with self._redis.pipeline(transaction=False) as pipe:
            await pipe.llen(self._ready_key)
            await pipe.zcard(self._delayed_key)
            await pipe.llen(self._processing_key)
            ready, delayed, processing = await pipe.execute()
        return int(ready) + int(delayed) + int(processing)

    async def ping(self) -> bool:
        try:
            self._chaos.maybe_raise_redis_failure()
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._redis.aclose()

    async def _promote_due_jobs(self, batch_size: int = 500) -> None:
        now = time.time()
        job_ids = await self._redis.zrangebyscore(self._delayed_key, 0, now, start=0, num=batch_size)
        if not job_ids:
            return
        async with self._redis.pipeline(transaction=True) as pipe:
            for job_id in job_ids:
                await pipe.zrem(self._delayed_key, job_id)
                await pipe.lpush(self._ready_key, job_id)
            await pipe.execute()

    async def _reclaim_expired_leases(self, *, limit: int) -> None:
        processing_ids = await self._redis.lrange(self._processing_key, 0, max(0, limit - 1))
        if not processing_ids:
            return

        async with self._redis.pipeline(transaction=False) as pipe:
            for job_id in processing_ids:
                await pipe.exists(self._lease_key(str(job_id)))
            lease_states = await pipe.execute()

        async with self._redis.pipeline(transaction=True) as pipe:
            moved = 0
            for idx, state in enumerate(lease_states):
                if int(state) != 0:
                    continue
                job_id = str(processing_ids[idx])
                await pipe.lrem(self._processing_key, 1, job_id)
                await pipe.lpush(self._ready_key, job_id)
                moved += 1
            if moved > 0:
                await pipe.execute()
                self._metrics.increment_counter("job_queue_reclaimed_total", labels={"backend": "redis"})

    async def _release_processing(self, *, job_id: str, lease_token: str, delete_job: bool) -> bool:
        result = await self._redis.eval(
            self._RELEASE_SCRIPT,
            3,
            self._processing_key,
            self._lease_key(job_id),
            self._job_key(job_id),
            lease_token,
            job_id,
            "1" if delete_job else "0",
        )
        return int(result or 0) == 1

    def _deserialize_job(self, *, job_id: str, job_data: dict[str, str], lease_token: str) -> JobEnvelope:
        payload_raw = job_data.get("payload") or "{}"
        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = {}

        return JobEnvelope(
            id=UUID(job_id),
            task_name=str(job_data.get("task_name") or ""),
            payload=dict(payload),
            attempts=int(job_data.get("attempts") or 0),
            max_retries=int(job_data.get("max_retries") or 3),
            retry_base_delay_seconds=float(job_data.get("retry_base_delay_seconds") or 1.0),
            created_at=float(job_data.get("created_at") or time.time()),
            available_at=float(job_data.get("available_at") or time.time()),
            last_error=(job_data.get("last_error") or None),
            delivery_token=lease_token,
            delivery_tag=job_id,
            backend="redis",
        )

    async def _send_to_dead_letter(self, job: JobEnvelope) -> None:
        dead_payload = {
            "id": str(job.id),
            "task_name": job.task_name,
            "payload": job.payload,
            "attempts": job.attempts,
            "max_retries": job.max_retries,
            "last_error": job.last_error,
            "created_at": job.created_at,
        }
        await self._redis.lpush(
            self._dead_key,
            json.dumps(dead_payload, separators=(",", ":"), default=str),
        )
        self._metrics.increment_counter("job_queue_dead_letter_total", labels={"backend": "redis"})

from __future__ import annotations

import json
import time
from typing import Any

from app.core.cache.cache_backend import CacheBackend
from app.core.prometheus_metrics import get_metrics_registry


class RedisCache(CacheBackend):
    """Redis-backed async cache implementation."""

    def __init__(self, redis_url: str, key_prefix: str = "crm"):
        try:
            from redis.asyncio import Redis
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("redis dependency is required for RedisCache") from exc

        self._client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._key_prefix = key_prefix
        self._metrics = get_metrics_registry()

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        cache_key = self._full_key(key)
        started_at = time.perf_counter()
        try:
            raw_value = await self._client.get(cache_key)
            self._metrics.observe_redis_latency(
                operation="get",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="get",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise
        if raw_value is None:
            self._metrics.increment_counter("cache_misses_total", labels={"backend": "redis"})
            return None
        self._metrics.increment_counter("cache_hits_total", labels={"backend": "redis"})
        return json.loads(raw_value)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        cache_key = self._full_key(key)
        encoded = json.dumps(value, separators=(",", ":"), default=str)
        started_at = time.perf_counter()
        try:
            await self._client.set(cache_key, encoded, ex=max(ttl_seconds, 1))
            self._metrics.observe_redis_latency(
                operation="set",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="set",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        cache_key = self._full_key(key)
        encoded = json.dumps(value, separators=(",", ":"), default=str)
        started_at = time.perf_counter()
        try:
            result = await self._client.set(cache_key, encoded, ex=max(ttl_seconds, 1), nx=True)
            self._metrics.observe_redis_latency(
                operation="set_if_absent",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
            return bool(result)
        except Exception:
            self._metrics.observe_redis_latency(
                operation="set_if_absent",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def delete(self, key: str) -> None:
        cache_key = self._full_key(key)
        started_at = time.perf_counter()
        try:
            await self._client.delete(cache_key)
            self._metrics.observe_redis_latency(
                operation="delete",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="delete",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        full_keys = [self._full_key(key) for key in keys]
        started_at = time.perf_counter()
        try:
            await self._client.delete(*full_keys)
            self._metrics.observe_redis_latency(
                operation="delete_many",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="delete_many",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def delete_by_prefix(self, prefix: str) -> None:
        pattern = f"{self._full_key(prefix)}*"
        cursor = 0
        started_at = time.perf_counter()
        try:
            while True:
                cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=500)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
            self._metrics.observe_redis_latency(
                operation="delete_by_prefix",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="delete_by_prefix",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def sadd(self, key: str, member: str) -> None:
        started_at = time.perf_counter()
        try:
            await self._client.sadd(self._full_key(key), member)
            self._metrics.observe_redis_latency(
                operation="sadd",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="sadd",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def smembers(self, key: str) -> set[str]:
        started_at = time.perf_counter()
        try:
            members = set(await self._client.smembers(self._full_key(key)))
            self._metrics.observe_redis_latency(
                operation="smembers",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
            return members
        except Exception:
            self._metrics.observe_redis_latency(
                operation="smembers",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def delete_set(self, key: str) -> None:
        started_at = time.perf_counter()
        try:
            await self._client.delete(self._full_key(key))
            self._metrics.observe_redis_latency(
                operation="delete_set",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
        except Exception:
            self._metrics.observe_redis_latency(
                operation="delete_set",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        cache_key = self._full_key(key)
        started_at = time.perf_counter()
        try:
            async with self._client.pipeline(transaction=True) as pipe:
                await pipe.incrby(cache_key, amount)
                await pipe.ttl(cache_key)
                result = await pipe.execute()

            current = int(result[0])
            ttl = int(result[1])
            if ttl < 0:
                await self._client.expire(cache_key, max(ttl_seconds, 1))
            self._metrics.observe_redis_latency(
                operation="increment",
                duration_seconds=time.perf_counter() - started_at,
                success=True,
            )
            return current
        except Exception:
            self._metrics.observe_redis_latency(
                operation="increment",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            raise

    async def ping(self) -> bool:
        started_at = time.perf_counter()
        try:
            result = bool(await self._client.ping())
            self._metrics.observe_redis_latency(
                operation="ping",
                duration_seconds=time.perf_counter() - started_at,
                success=result,
            )
            return result
        except Exception:
            self._metrics.observe_redis_latency(
                operation="ping",
                duration_seconds=time.perf_counter() - started_at,
                success=False,
            )
            return False

    async def close(self) -> None:
        await self._client.aclose()

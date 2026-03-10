from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from app.core.config import get_settings
from app.core.prometheus_metrics import get_metrics_registry
from app.core.reliability.chaos import get_chaos_engine


@dataclass(frozen=True)
class DistributedLockHandle:
    key: str
    owner_token: str
    fencing_token: int
    expires_at_monotonic: float


class DistributedLockManager:
    """Distributed lock manager contract."""

    async def acquire(self, *, key: str, ttl_seconds: float) -> DistributedLockHandle | None:
        raise NotImplementedError

    async def release(self, handle: DistributedLockHandle) -> bool:
        raise NotImplementedError


class NoopDistributedLockManager(DistributedLockManager):
    """Fallback lock manager when distributed backend is unavailable."""

    async def acquire(self, *, key: str, ttl_seconds: float) -> DistributedLockHandle | None:
        owner_token = uuid4().hex
        ttl = max(1.0, ttl_seconds)
        return DistributedLockHandle(
            key=key,
            owner_token=owner_token,
            fencing_token=0,
            expires_at_monotonic=time.monotonic() + ttl,
        )

    async def release(self, handle: DistributedLockHandle) -> bool:
        return True


class RedisDistributedLockManager(DistributedLockManager):
    """Redis-based lock manager with fencing tokens and owner-safe release."""

    _ACQUIRE_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
  local token = redis.call('INCR', KEYS[2])
  redis.call('HMSET', KEYS[1], 'owner', ARGV[1], 'fencing', token)
  redis.call('PEXPIRE', KEYS[1], ARGV[2])
  return token
end
return 0
""".strip()

    _RELEASE_SCRIPT = """
if redis.call('HGET', KEYS[1], 'owner') == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
""".strip()

    def __init__(self, redis_url: str, prefix: str = "crm:lock") -> None:
        try:
            from redis.asyncio import Redis
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("redis dependency is required for RedisDistributedLockManager") from exc

        self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._prefix = prefix
        self._metrics = get_metrics_registry()
        self._chaos = get_chaos_engine()

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def _fencing_key(self, key: str) -> str:
        return f"{self._prefix}:fencing:{key}"

    async def acquire(self, *, key: str, ttl_seconds: float) -> DistributedLockHandle | None:
        self._chaos.maybe_raise_redis_failure()
        owner_token = uuid4().hex
        lock_key = self._full_key(key)
        fencing_key = self._fencing_key(key)
        ttl_ms = max(1000, int(ttl_seconds * 1000))
        fencing_token = await self._redis.eval(
            self._ACQUIRE_SCRIPT,
            2,
            lock_key,
            fencing_key,
            owner_token,
            str(ttl_ms),
        )
        if int(fencing_token or 0) <= 0:
            self._metrics.increment_counter("distributed_lock_contention_total", labels={"backend": "redis"})
            return None

        self._metrics.increment_counter("distributed_lock_acquire_total", labels={"backend": "redis"})
        return DistributedLockHandle(
            key=lock_key,
            owner_token=owner_token,
            fencing_token=int(fencing_token),
            expires_at_monotonic=time.monotonic() + max(1.0, ttl_seconds),
        )

    async def release(self, handle: DistributedLockHandle) -> bool:
        try:
            self._chaos.maybe_raise_redis_failure()
            result = await self._redis.eval(
                self._RELEASE_SCRIPT,
                1,
                handle.key,
                handle.owner_token,
            )
            released = int(result) == 1
            if released:
                self._metrics.increment_counter("distributed_lock_release_total", labels={"backend": "redis"})
            return released
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_distributed_lock_manager() -> DistributedLockManager:
    settings = get_settings()
    if settings.lock_backend == "redis":
        try:
            return RedisDistributedLockManager(redis_url=settings.redis_url, prefix=settings.lock_namespace)
        except Exception:
            return NoopDistributedLockManager()
    return NoopDistributedLockManager()

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings


class CacheBackend(ABC):
    """Async cache backend contract."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Return cached value by key."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store value with ttl."""

    @abstractmethod
    async def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Store value only when key does not exist."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> None:
        """Delete many keys from cache."""

    @abstractmethod
    async def delete_by_prefix(self, prefix: str) -> None:
        """Delete all keys with prefix."""

    @abstractmethod
    async def sadd(self, key: str, member: str) -> None:
        """Add member to set stored under key."""

    @abstractmethod
    async def smembers(self, key: str) -> set[str]:
        """Return set members for key."""

    @abstractmethod
    async def delete_set(self, key: str) -> None:
        """Delete set key."""

    @abstractmethod
    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        """Increment numeric key and set TTL for first write."""

    @abstractmethod
    async def ping(self) -> bool:
        """Return backend health status."""

    @abstractmethod
    async def close(self) -> None:
        """Close backend resources."""


class SyncCacheAdapter:
    """Sync adapter for async cache backends."""

    def __init__(self, backend: CacheBackend):
        self.backend = backend

    def get(self, key: str) -> Any | None:
        return _run_async(self.backend.get(key))

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        _run_async(self.backend.set(key, value, ttl_seconds))

    def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        return bool(_run_async(self.backend.set_if_absent(key, value, ttl_seconds)))

    def delete(self, key: str) -> None:
        _run_async(self.backend.delete(key))

    def delete_many(self, keys: list[str]) -> None:
        _run_async(self.backend.delete_many(keys))

    def delete_by_prefix(self, prefix: str) -> None:
        _run_async(self.backend.delete_by_prefix(prefix))

    def sadd(self, key: str, member: str) -> None:
        _run_async(self.backend.sadd(key, member))

    def smembers(self, key: str) -> set[str]:
        return set(_run_async(self.backend.smembers(key)))

    def delete_set(self, key: str) -> None:
        _run_async(self.backend.delete_set(key))

    def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        return int(_run_async(self.backend.increment(key, amount, ttl_seconds)))

    def ping(self) -> bool:
        return bool(_run_async(self.backend.ping()))


def build_tenant_cache_key(tenant_id: UUID | str, namespace: str, *parts: str) -> str:
    """Build tenant-scoped cache key."""
    normalized_parts = [str(tenant_id), namespace, *[part for part in parts if part]]
    return ":".join(normalized_parts)


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Sync cache adapter cannot be used inside an active event loop")


@lru_cache(maxsize=1)
def get_cache_backend(settings: Settings | None = None) -> CacheBackend:
    """Create and cache the configured cache backend instance."""
    from app.core.cache.memory_cache import MemoryCache
    from app.core.cache.redis_cache import RedisCache

    cfg = settings or get_settings()
    if cfg.cache_backend == "redis":
        return RedisCache(redis_url=cfg.redis_url, key_prefix=cfg.cache_key_prefix)
    return MemoryCache(key_prefix=cfg.cache_key_prefix)


def get_sync_cache_adapter() -> SyncCacheAdapter:
    """Return sync cache adapter for service layer."""
    return SyncCacheAdapter(get_cache_backend())

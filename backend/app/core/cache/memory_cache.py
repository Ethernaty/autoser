from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.prometheus_metrics import get_metrics_registry
from app.core.runtime_guards import assert_bounded_structure
from app.core.cache.cache_backend import CacheBackend


@dataclass
class _CacheItem:
    value: Any
    expires_at: float


class MemoryCache(CacheBackend):
    """In-memory async cache backend with TTL support."""

    def __init__(self, key_prefix: str = "crm"):
        self._key_prefix = key_prefix
        self._items: dict[str, _CacheItem] = {}
        self._sets: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()
        self._max_items = get_settings().memory_cache_max_items
        self._metrics = get_metrics_registry()

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        cache_key = self._full_key(key)
        async with self._lock:
            item = self._items.get(cache_key)
            if item is None:
                self._metrics.increment_counter("cache_misses_total", labels={"backend": "memory"})
                return None
            if item.expires_at < time.monotonic():
                self._items.pop(cache_key, None)
                self._metrics.increment_counter("cache_misses_total", labels={"backend": "memory"})
                return None
            self._metrics.increment_counter("cache_hits_total", labels={"backend": "memory"})
            return item.value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        cache_key = self._full_key(key)
        expires_at = time.monotonic() + max(ttl_seconds, 1)
        async with self._lock:
            self._items[cache_key] = _CacheItem(value=value, expires_at=expires_at)
            assert_bounded_structure(name="memory_cache_items", size=len(self._items), limit=self._max_items)

    async def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        cache_key = self._full_key(key)
        expires_at = time.monotonic() + max(ttl_seconds, 1)
        async with self._lock:
            current = self._items.get(cache_key)
            if current is not None and current.expires_at >= time.monotonic():
                return False
            self._items[cache_key] = _CacheItem(value=value, expires_at=expires_at)
            assert_bounded_structure(name="memory_cache_items", size=len(self._items), limit=self._max_items)
            return True

    async def delete(self, key: str) -> None:
        cache_key = self._full_key(key)
        async with self._lock:
            self._items.pop(cache_key, None)

    async def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        async with self._lock:
            for key in keys:
                self._items.pop(self._full_key(key), None)

    async def delete_by_prefix(self, prefix: str) -> None:
        cache_prefix = self._full_key(prefix)
        async with self._lock:
            keys = [key for key in self._items if key.startswith(cache_prefix)]
            for key in keys:
                self._items.pop(key, None)

    async def sadd(self, key: str, member: str) -> None:
        set_key = self._full_key(key)
        async with self._lock:
            self._sets.setdefault(set_key, set()).add(member)

    async def smembers(self, key: str) -> set[str]:
        set_key = self._full_key(key)
        async with self._lock:
            return set(self._sets.get(set_key, set()))

    async def delete_set(self, key: str) -> None:
        set_key = self._full_key(key)
        async with self._lock:
            self._sets.pop(set_key, None)

    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        cache_key = self._full_key(key)
        now = time.monotonic()
        expires_at = now + max(ttl_seconds, 1)
        async with self._lock:
            current = self._items.get(cache_key)
            if current is None or current.expires_at < now:
                next_value = amount
                self._items[cache_key] = _CacheItem(value=next_value, expires_at=expires_at)
                assert_bounded_structure(name="memory_cache_items", size=len(self._items), limit=self._max_items)
                return int(next_value)
            try:
                current_value = int(current.value)
            except Exception:
                current_value = 0
            next_value = current_value + amount
            self._items[cache_key] = _CacheItem(value=next_value, expires_at=current.expires_at)
            assert_bounded_structure(name="memory_cache_items", size=len(self._items), limit=self._max_items)
            return int(next_value)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        async with self._lock:
            self._items.clear()
            self._sets.clear()

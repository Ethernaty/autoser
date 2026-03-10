from __future__ import annotations

from typing import Any

from app.core.cache.cache_backend import CacheBackend
from app.core.circuit_breaker import AsyncCircuitBreaker


class CircuitBreakerCacheBackend(CacheBackend):
    """Protect cache backend with circuit breaker without split-brain fallback."""

    def __init__(self, *, primary: CacheBackend, breaker: AsyncCircuitBreaker) -> None:
        self._primary = primary
        self._breaker = breaker

    async def get(self, key: str) -> Any | None:
        return await self._breaker.call(lambda: self._primary.get(key))

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._breaker.call(lambda: self._primary.set(key, value, ttl_seconds))

    async def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        return bool(await self._breaker.call(lambda: self._primary.set_if_absent(key, value, ttl_seconds)))

    async def delete(self, key: str) -> None:
        await self._breaker.call(lambda: self._primary.delete(key))

    async def delete_many(self, keys: list[str]) -> None:
        await self._breaker.call(lambda: self._primary.delete_many(keys))

    async def delete_by_prefix(self, prefix: str) -> None:
        await self._breaker.call(lambda: self._primary.delete_by_prefix(prefix))

    async def sadd(self, key: str, member: str) -> None:
        await self._breaker.call(lambda: self._primary.sadd(key, member))

    async def smembers(self, key: str) -> set[str]:
        result = await self._breaker.call(lambda: self._primary.smembers(key))
        return set(result)

    async def delete_set(self, key: str) -> None:
        await self._breaker.call(lambda: self._primary.delete_set(key))

    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        result = await self._breaker.call(lambda: self._primary.increment(key, amount, ttl_seconds))
        return int(result)

    async def ping(self) -> bool:
        return bool(await self._breaker.call(lambda: self._primary.ping()))

    async def close(self) -> None:
        await self._primary.close()

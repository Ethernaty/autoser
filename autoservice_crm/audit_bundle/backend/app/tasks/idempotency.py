from __future__ import annotations

from dataclasses import dataclass

from app.core.cache import CacheBackend, get_cache_backend


@dataclass
class TaskIdempotencyStore:
    cache: CacheBackend
    ttl_seconds: int = 3600

    @classmethod
    def create_default(cls, *, ttl_seconds: int = 3600) -> "TaskIdempotencyStore":
        return cls(cache=get_cache_backend(), ttl_seconds=ttl_seconds)

    async def reserve(self, *, key: str) -> bool:
        return bool(await self.cache.set_if_absent(f"task:idempotency:{key}", 1, self.ttl_seconds))

    async def mark_done(self, *, key: str) -> None:
        await self.cache.set(f"task:idempotency:{key}", "done", self.ttl_seconds)

    async def exists(self, *, key: str) -> bool:
        return await self.cache.get(f"task:idempotency:{key}") is not None

"""Thread-safe synchronous Redis access sharing keys with the async cache.

Worker-thread services must not run the application's async connection pool
inside temporary event loops. Redis' synchronous pool owns no asyncio futures.
"""
import json
from typing import Any

from redis import Redis

from app.core.cache.cache_backend import SyncCacheAdapter


class SyncRedisCache(SyncCacheAdapter):
    def __init__(self, redis_url: str, key_prefix: str):
        self._client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        value = self._client.get(self._key(key))
        return json.loads(value) if value is not None else None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._client.set(self._key(key), json.dumps(value, separators=(",", ":"), default=str), ex=max(1, ttl_seconds))

    def set_if_absent(self, key: str, value: Any, ttl_seconds: int) -> bool:
        return bool(self._client.set(self._key(key), json.dumps(value, separators=(",", ":"), default=str), ex=max(1, ttl_seconds), nx=True))

    def delete(self, key: str) -> None:
        self._client.delete(self._key(key))

    def delete_many(self, keys: list[str]) -> None:
        if keys:
            self._client.delete(*(self._key(key) for key in keys))

    def delete_by_prefix(self, prefix: str) -> None:
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=f"{self._key(prefix)}*", count=500)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break

    def sadd(self, key: str, member: str) -> None:
        self._client.sadd(self._key(key), member)

    def smembers(self, key: str) -> set[str]:
        return set(self._client.smembers(self._key(key)))

    def delete_set(self, key: str) -> None:
        self.delete(key)

    def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        script = "local n=redis.call('INCRBY',KEYS[1],ARGV[1]); if redis.call('TTL',KEYS[1])<0 then redis.call('EXPIRE',KEYS[1],ARGV[2]) end; return n"
        return int(self._client.eval(script, 1, self._key(key), amount, max(1, ttl_seconds)))

    def ping(self) -> bool:
        return bool(self._client.ping())

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Awaitable, Callable


FailoverHook = Callable[[str], Awaitable[None]]


@dataclass
class FailoverRegistry:
    read_replica_hooks: list[FailoverHook] = field(default_factory=list)
    queue_switch_hooks: list[FailoverHook] = field(default_factory=list)
    cache_switch_hooks: list[FailoverHook] = field(default_factory=list)


class FailoverManager:
    """Pluggable failover hook manager."""

    def __init__(self) -> None:
        self._registry = FailoverRegistry()
        self._lock = asyncio.Lock()

    async def register_read_replica_failover_hook(self, hook: FailoverHook) -> None:
        async with self._lock:
            self._registry.read_replica_hooks.append(hook)

    async def register_queue_backend_switch_hook(self, hook: FailoverHook) -> None:
        async with self._lock:
            self._registry.queue_switch_hooks.append(hook)

    async def register_cache_backend_switch_hook(self, hook: FailoverHook) -> None:
        async with self._lock:
            self._registry.cache_switch_hooks.append(hook)

    async def trigger_read_replica_failover(self, reason: str) -> None:
        await self._run_hooks(self._registry.read_replica_hooks, reason)

    async def trigger_queue_backend_switch(self, reason: str) -> None:
        await self._run_hooks(self._registry.queue_switch_hooks, reason)

    async def trigger_cache_backend_switch(self, reason: str) -> None:
        await self._run_hooks(self._registry.cache_switch_hooks, reason)

    async def _run_hooks(self, hooks: list[FailoverHook], reason: str) -> None:
        if not hooks:
            return
        for hook in list(hooks):
            try:
                await hook(reason)
            except Exception:
                continue

    async def status(self) -> dict[str, int]:
        async with self._lock:
            return {
                "read_replica_hooks": len(self._registry.read_replica_hooks),
                "queue_switch_hooks": len(self._registry.queue_switch_hooks),
                "cache_switch_hooks": len(self._registry.cache_switch_hooks),
            }


@lru_cache(maxsize=1)
def get_failover_manager() -> FailoverManager:
    return FailoverManager()

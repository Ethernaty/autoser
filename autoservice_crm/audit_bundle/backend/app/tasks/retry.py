from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class TaskRetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 5.0


async def run_with_task_retry(operation: Callable[[], Awaitable[T]], *, policy: TaskRetryPolicy) -> T:
    attempt = 0
    while True:
        attempt += 1
        try:
            return await operation()
        except Exception:
            if attempt >= max(1, policy.attempts):
                raise
            backoff = min(policy.max_delay_seconds, policy.base_delay_seconds * (2 ** (attempt - 1)))
            await asyncio.sleep(backoff)

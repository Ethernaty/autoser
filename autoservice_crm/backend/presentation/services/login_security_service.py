from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class LoginRateDecision:
    allowed: bool
    retry_after_seconds: int


class LoginRateLimiter:
    """In-memory login limiter keyed by client fingerprint."""

    def __init__(self, *, max_attempts: int = 8, window_seconds: int = 300) -> None:
        self._max_attempts = max(1, max_attempts)
        self._window_seconds = max(30, window_seconds)
        self._hits: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, *, key: str) -> LoginRateDecision:
        now = time.monotonic()
        async with self._lock:
            history = self._hits.get(key, [])
            threshold = now - self._window_seconds
            history = [item for item in history if item >= threshold]

            if len(history) >= self._max_attempts:
                oldest = min(history)
                retry_after = max(1, int((oldest + self._window_seconds) - now))
                self._hits[key] = history
                return LoginRateDecision(allowed=False, retry_after_seconds=retry_after)

            history.append(now)
            self._hits[key] = history
            return LoginRateDecision(allowed=True, retry_after_seconds=0)

    async def reset(self, *, key: str) -> None:
        async with self._lock:
            self._hits.pop(key, None)


_limiter = LoginRateLimiter()


def get_login_rate_limiter() -> LoginRateLimiter:
    return _limiter

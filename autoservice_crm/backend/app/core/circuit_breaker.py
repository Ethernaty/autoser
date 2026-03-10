from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Awaitable, Callable, TypeVar


T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitSnapshot:
    state: CircuitState
    failures: int
    opened_at: float | None


class AsyncCircuitBreaker:
    """
    Async circuit breaker for unstable dependencies (for example Redis).

    Closed:
    - all requests flow through
    Open:
    - requests fail-fast until recovery timeout elapsed
    Half-open:
    - one probe request is allowed; success closes circuit, failure opens it again
    """

    def __init__(self, *, failure_threshold: int, recovery_timeout_seconds: float):
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_timeout_seconds = max(1.0, recovery_timeout_seconds)
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()
        self._half_open_probe_in_flight = False

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            await self._allow_or_raise_locked()
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_probe_in_flight:
                    raise RuntimeError("circuit_open")
                self._half_open_probe_in_flight = True

        try:
            result = await operation()
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def snapshot(self) -> CircuitSnapshot:
        async with self._lock:
            return CircuitSnapshot(
                state=self._state,
                failures=self._failures,
                opened_at=self._opened_at,
            )

    async def _allow_or_raise_locked(self) -> None:
        if self._state == CircuitState.CLOSED:
            return
        if self._state == CircuitState.OPEN:
            if self._opened_at is None:
                raise RuntimeError("circuit_open")
            if (monotonic() - self._opened_at) >= self._recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                return
            raise RuntimeError("circuit_open")

    async def _on_success(self) -> None:
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None
            self._half_open_probe_in_flight = False

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            self._half_open_probe_in_flight = False

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = monotonic()
                return

            if self._failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = monotonic()

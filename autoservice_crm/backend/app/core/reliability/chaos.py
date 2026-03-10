from __future__ import annotations

import asyncio
import random
import threading
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Callable, TypeVar, cast

from app.core.config import get_settings


T = TypeVar("T")


class ChaosInjectedError(RuntimeError):
    """Raised when chaos fault injection is active."""


@dataclass(frozen=True)
class ChaosPolicy:
    enabled: bool
    redis_failure_rate: float
    db_latency_ms: int
    queue_delay_ms: int
    event_drop_rate: float
    exception_rate: float

    @staticmethod
    def sanitize_value(value: float, *, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, fallback: "ChaosPolicy") -> "ChaosPolicy":
        return cls(
            enabled=bool(payload.get("enabled", fallback.enabled)),
            redis_failure_rate=cls.sanitize_value(
                float(payload.get("redis_failure_rate", fallback.redis_failure_rate)),
                min_value=0.0,
                max_value=1.0,
            ),
            db_latency_ms=max(0, int(payload.get("db_latency_ms", fallback.db_latency_ms))),
            queue_delay_ms=max(0, int(payload.get("queue_delay_ms", fallback.queue_delay_ms))),
            event_drop_rate=cls.sanitize_value(
                float(payload.get("event_drop_rate", fallback.event_drop_rate)),
                min_value=0.0,
                max_value=1.0,
            ),
            exception_rate=cls.sanitize_value(
                float(payload.get("exception_rate", fallback.exception_rate)),
                min_value=0.0,
                max_value=1.0,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChaosEngine:
    """Thread-safe runtime chaos policy with async/sync injection hooks."""

    def __init__(self, policy: ChaosPolicy) -> None:
        self._policy = policy
        self._lock = threading.Lock()
        self._rng = random.Random()

    def get_policy(self) -> ChaosPolicy:
        with self._lock:
            return self._policy

    def set_policy(self, updates: dict[str, Any]) -> ChaosPolicy:
        with self._lock:
            next_policy = ChaosPolicy.from_dict(updates, fallback=self._policy)
            self._policy = next_policy
            return next_policy

    def reset_policy(self) -> ChaosPolicy:
        settings = get_settings()
        baseline = build_default_policy(
            enabled=settings.chaos_enabled,
            redis_failure_rate=settings.chaos_redis_failure_rate,
            db_latency_ms=settings.chaos_db_latency_ms,
            queue_delay_ms=settings.chaos_queue_delay_ms,
            event_drop_rate=settings.chaos_event_drop_rate,
            exception_rate=settings.chaos_exception_rate,
        )
        with self._lock:
            self._policy = baseline
            return baseline

    def maybe_raise_redis_failure(self) -> None:
        policy = self.get_policy()
        if not policy.enabled:
            return
        if self._rng.random() < policy.redis_failure_rate:
            raise ChaosInjectedError("chaos_redis_failure")

    def maybe_add_db_latency_sync(self) -> None:
        policy = self.get_policy()
        if not policy.enabled or policy.db_latency_ms <= 0:
            return
        delay = policy.db_latency_ms / 1000.0
        time.sleep(delay)

    async def maybe_add_queue_delay_async(self) -> None:
        policy = self.get_policy()
        if not policy.enabled or policy.queue_delay_ms <= 0:
            return
        delay = policy.queue_delay_ms / 1000.0
        await asyncio.sleep(delay)

    def should_drop_event(self) -> bool:
        policy = self.get_policy()
        if not policy.enabled:
            return False
        return self._rng.random() < policy.event_drop_rate

    def maybe_raise_random_exception(self) -> None:
        policy = self.get_policy()
        if not policy.enabled:
            return
        if self._rng.random() < policy.exception_rate:
            raise ChaosInjectedError("chaos_random_exception")


def build_default_policy(
    *,
    enabled: bool,
    redis_failure_rate: float,
    db_latency_ms: int,
    queue_delay_ms: int,
    event_drop_rate: float,
    exception_rate: float,
) -> ChaosPolicy:
    return ChaosPolicy(
        enabled=bool(enabled),
        redis_failure_rate=ChaosPolicy.sanitize_value(float(redis_failure_rate), min_value=0.0, max_value=1.0),
        db_latency_ms=max(0, int(db_latency_ms)),
        queue_delay_ms=max(0, int(queue_delay_ms)),
        event_drop_rate=ChaosPolicy.sanitize_value(float(event_drop_rate), min_value=0.0, max_value=1.0),
        exception_rate=ChaosPolicy.sanitize_value(float(exception_rate), min_value=0.0, max_value=1.0),
    )


@lru_cache(maxsize=1)
def get_chaos_engine() -> ChaosEngine:
    settings = get_settings()
    policy = build_default_policy(
        enabled=settings.chaos_enabled,
        redis_failure_rate=settings.chaos_redis_failure_rate,
        db_latency_ms=settings.chaos_db_latency_ms,
        queue_delay_ms=settings.chaos_queue_delay_ms,
        event_drop_rate=settings.chaos_event_drop_rate,
        exception_rate=settings.chaos_exception_rate,
    )
    return ChaosEngine(policy)


def chaos_fault_injection(
    fault_hook: Callable[[], None],
    *,
    async_fault_hook: Callable[[], "asyncio.Future[Any]"] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for sync/async callable fault injection."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                fault_hook()
                if async_fault_hook is not None:
                    await async_fault_hook()
                return await cast(Callable[..., Any], func)(*args, **kwargs)

            return cast(Callable[..., T], async_wrapper)

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            fault_hook()
            return func(*args, **kwargs)

        return cast(Callable[..., T], sync_wrapper)

    return decorator

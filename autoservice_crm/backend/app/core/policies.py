from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError, TimeoutError as SQLAlchemyTimeoutError

from app.core.config import get_settings


T = TypeVar("T")

# PostgreSQL transient classes/codes.
_TRANSIENT_SQLSTATE_PREFIXES = {
    "08",  # connection exception
    "40",  # transaction rollback
    "53",  # insufficient resources
    "57",  # operator intervention
}
_TRANSIENT_SQLSTATE_CODES = {
    "40001",  # serialization_failure
    "40P01",  # deadlock_detected
    "53300",  # too_many_connections
    "57P01",  # admin_shutdown
    "57P02",  # crash_shutdown
    "57P03",  # cannot_connect_now
}


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int
    base_delay_seconds: float
    use_timeout: bool


def read_retry_policy() -> RetryPolicy:
    settings = get_settings()
    return RetryPolicy(
        attempts=max(1, settings.db_retry_attempts),
        base_delay_seconds=max(0.01, settings.db_retry_base_delay_seconds),
        use_timeout=True,
    )


def write_retry_policy(*, idempotent: bool = False) -> RetryPolicy:
    settings = get_settings()
    # Non-idempotent writes MUST never be retried.
    attempts = max(1, settings.db_retry_attempts) if idempotent else 1
    return RetryPolicy(
        attempts=attempts,
        base_delay_seconds=max(0.01, settings.db_retry_base_delay_seconds),
        use_timeout=False,
    )


def is_transient_db_error(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, SQLAlchemyTimeoutError)):
        return True

    if isinstance(exc, DBAPIError):
        sqlstate = getattr(getattr(exc, "orig", None), "pgcode", None)
        if isinstance(sqlstate, str):
            if sqlstate in _TRANSIENT_SQLSTATE_CODES:
                return True
            if len(sqlstate) >= 2 and sqlstate[:2] in _TRANSIENT_SQLSTATE_PREFIXES:
                return True
        return bool(getattr(exc, "connection_invalidated", False))

    return False


async def run_with_timeout(operation: Callable[[], Awaitable[T]], *, timeout_seconds: float) -> T:
    """Run async operation with explicit timeout."""
    return await asyncio.wait_for(operation(), timeout=max(0.1, timeout_seconds))


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
) -> T:
    """Retry operation only for transient DB failures according to policy."""
    current_attempt = 0
    while True:
        current_attempt += 1
        try:
            return await operation()
        except Exception as exc:
            if current_attempt >= policy.attempts or not is_transient_db_error(exc):
                raise
            delay = policy.base_delay_seconds * (2 ** (current_attempt - 1))
            jittered = delay * (0.5 + random.random())
            await asyncio.sleep(min(jittered, 1.5))

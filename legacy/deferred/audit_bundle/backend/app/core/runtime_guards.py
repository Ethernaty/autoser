from __future__ import annotations

import asyncio
from contextvars import ContextVar


_uow_depth: ContextVar[int] = ContextVar("uow_depth", default=0)


def assert_sync_db_call_safe() -> None:
    """Crash fast if sync DB call is executed in async event-loop thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if loop.is_running():
        raise RuntimeError("sync_db_call_in_async_context")


def push_uow_depth() -> None:
    depth = _uow_depth.get()
    if depth > 0:
        raise RuntimeError("nested_transaction_detected")
    _uow_depth.set(depth + 1)


def pop_uow_depth() -> None:
    depth = _uow_depth.get()
    _uow_depth.set(max(0, depth - 1))


def assert_bounded_structure(*, name: str, size: int, limit: int) -> None:
    if size > limit:
        raise RuntimeError(f"unbounded_structure_detected:{name}:{size}>{limit}")

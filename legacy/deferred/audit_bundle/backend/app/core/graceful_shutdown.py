from __future__ import annotations

import asyncio
import signal
from functools import lru_cache


class GracefulShutdownManager:
    """Tracks in-flight requests and coordinates graceful drain."""

    def __init__(self) -> None:
        self._draining = False
        self._inflight = 0
        self._lock = asyncio.Lock()
        self._drained = asyncio.Event()
        self._drained.set()

    @property
    def is_draining(self) -> bool:
        return self._draining

    async def begin_shutdown(self) -> None:
        async with self._lock:
            self._draining = True
            if self._inflight == 0:
                self._drained.set()

    async def on_request_start(self) -> None:
        async with self._lock:
            if self._draining:
                raise RuntimeError("server_draining")
            self._inflight += 1
            self._drained.clear()

    async def on_request_end(self) -> None:
        async with self._lock:
            if self._inflight > 0:
                self._inflight -= 1
            if self._inflight == 0:
                self._drained.set()

    async def wait_for_drain(self, timeout_seconds: float) -> bool:
        try:
            await asyncio.wait_for(self._drained.wait(), timeout=max(0.1, timeout_seconds))
            return True
        except asyncio.TimeoutError:
            return False

    def install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._schedule_shutdown)
            except (NotImplementedError, RuntimeError, ValueError):
                continue

    def _schedule_shutdown(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.begin_shutdown())
        except RuntimeError:
            return


@lru_cache(maxsize=1)
def get_shutdown_manager() -> GracefulShutdownManager:
    return GracefulShutdownManager()

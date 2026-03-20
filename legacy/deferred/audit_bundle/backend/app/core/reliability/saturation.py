from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.database import engine
from app.core.jobs import get_job_queue
from app.core.prometheus_metrics import PrometheusMetricsRegistry, get_metrics_registry


@dataclass(frozen=True)
class SaturationSignal:
    name: str
    value: float
    threshold: float
    unit: str
    saturated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "unit": self.unit,
            "saturated": self.saturated,
        }


@dataclass(frozen=True)
class SaturationReport:
    collected_at_unix: float
    threadpool_saturation: SaturationSignal
    db_pool_exhaustion: SaturationSignal
    lock_contention_storm: SaturationSignal
    queue_backlog_growth: SaturationSignal
    event_loop_lag: SaturationSignal
    queue_depth: int
    db_checked_out: int
    db_pool_size: int
    saturation_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "collected_at_unix": self.collected_at_unix,
            "signals": {
                "threadpool_saturation": self.threadpool_saturation.to_dict(),
                "db_pool_exhaustion": self.db_pool_exhaustion.to_dict(),
                "lock_contention_storm": self.lock_contention_storm.to_dict(),
                "queue_backlog_growth": self.queue_backlog_growth.to_dict(),
                "event_loop_lag": self.event_loop_lag.to_dict(),
            },
            "queue_depth": self.queue_depth,
            "db_checked_out": self.db_checked_out,
            "db_pool_size": self.db_pool_size,
            "saturation_score": self.saturation_score,
        }


class SaturationDetector:
    """Runtime saturation detector for internal certification endpoints."""

    def __init__(self, metrics: PrometheusMetricsRegistry) -> None:
        self._metrics = metrics
        self._settings = get_settings()
        self._state_lock = Lock()
        self._prev_timestamp = time.time()
        self._prev_queue_depth = 0
        self._prev_lock_contention = 0.0

    async def collect(self) -> SaturationReport:
        collected_at = time.time()
        snapshot = self._metrics.snapshot()

        threadpool_latency_ms = await self._measure_threadpool_dispatch_ms()
        event_loop_lag_ms = await self._measure_event_loop_lag_ms()
        queue_depth = await self._safe_queue_depth()
        pool_size, checked_out = self._db_pool_usage()
        lock_contention_total = self._counter_sum(snapshot=snapshot, metric_name="distributed_lock_contention_total")

        with self._state_lock:
            elapsed = max(1e-6, collected_at - self._prev_timestamp)
            queue_growth_per_sec = (queue_depth - self._prev_queue_depth) / elapsed
            lock_contention_rate = (lock_contention_total - self._prev_lock_contention) / elapsed
            self._prev_timestamp = collected_at
            self._prev_queue_depth = queue_depth
            self._prev_lock_contention = lock_contention_total

        pool_capacity = max(1, pool_size)
        db_exhaustion_ratio = checked_out / pool_capacity

        threadpool_signal = SaturationSignal(
            name="threadpool_saturation",
            value=threadpool_latency_ms,
            threshold=float(self._settings.saturation_threadpool_dispatch_ms),
            unit="ms",
            saturated=threadpool_latency_ms >= float(self._settings.saturation_threadpool_dispatch_ms),
        )
        db_signal = SaturationSignal(
            name="db_pool_exhaustion",
            value=db_exhaustion_ratio,
            threshold=float(self._settings.saturation_db_pool_exhaustion_ratio),
            unit="ratio",
            saturated=db_exhaustion_ratio >= float(self._settings.saturation_db_pool_exhaustion_ratio),
        )
        lock_signal = SaturationSignal(
            name="lock_contention_storm",
            value=lock_contention_rate,
            threshold=float(self._settings.saturation_lock_contention_rate_per_sec),
            unit="events_per_sec",
            saturated=lock_contention_rate >= float(self._settings.saturation_lock_contention_rate_per_sec),
        )
        queue_signal = SaturationSignal(
            name="queue_backlog_growth",
            value=queue_growth_per_sec,
            threshold=float(self._settings.saturation_queue_backlog_growth_per_sec),
            unit="jobs_per_sec",
            saturated=queue_growth_per_sec >= float(self._settings.saturation_queue_backlog_growth_per_sec),
        )
        event_loop_signal = SaturationSignal(
            name="event_loop_lag",
            value=event_loop_lag_ms,
            threshold=float(self._settings.saturation_event_loop_lag_ms),
            unit="ms",
            saturated=event_loop_lag_ms >= float(self._settings.saturation_event_loop_lag_ms),
        )

        score = (
            (1.0 if threadpool_signal.saturated else 0.0)
            + (1.0 if db_signal.saturated else 0.0)
            + (1.0 if lock_signal.saturated else 0.0)
            + (1.0 if queue_signal.saturated else 0.0)
            + (1.0 if event_loop_signal.saturated else 0.0)
        ) / 5.0

        self._metrics.set_gauge("saturation_score", score)
        self._metrics.set_gauge("saturation_queue_depth", float(queue_depth))
        self._metrics.set_gauge("saturation_db_exhaustion_ratio", db_exhaustion_ratio)
        self._metrics.set_gauge("saturation_event_loop_lag_ms", event_loop_lag_ms)
        self._metrics.set_gauge("saturation_threadpool_dispatch_ms", threadpool_latency_ms)

        return SaturationReport(
            collected_at_unix=collected_at,
            threadpool_saturation=threadpool_signal,
            db_pool_exhaustion=db_signal,
            lock_contention_storm=lock_signal,
            queue_backlog_growth=queue_signal,
            event_loop_lag=event_loop_signal,
            queue_depth=queue_depth,
            db_checked_out=checked_out,
            db_pool_size=pool_size,
            saturation_score=score,
        )

    async def _measure_threadpool_dispatch_ms(self) -> float:
        started = time.perf_counter()
        await asyncio.to_thread(lambda: None)
        return max(0.0, (time.perf_counter() - started) * 1000.0)

    async def _measure_event_loop_lag_ms(self) -> float:
        started = time.perf_counter()
        await asyncio.sleep(0.05)
        elapsed = time.perf_counter() - started
        return max(0.0, (elapsed - 0.05) * 1000.0)

    async def _safe_queue_depth(self) -> int:
        try:
            return int(await get_job_queue().size())
        except Exception:
            return 0

    @staticmethod
    def _db_pool_usage() -> tuple[int, int]:
        pool = engine.pool
        try:
            size = int(pool.size())  # type: ignore[call-arg]
        except Exception:
            size = 0
        try:
            checked_out = int(pool.checkedout())  # type: ignore[call-arg]
        except Exception:
            checked_out = 0
        return max(1, size), max(0, checked_out)

    @staticmethod
    def _counter_sum(*, snapshot: dict[str, Any], metric_name: str) -> float:
        total = 0.0
        for row in snapshot.get("counters", []):
            if row.get("name") == metric_name:
                total += float(row.get("value", 0.0))
        return total


@lru_cache(maxsize=1)
def get_saturation_detector() -> SaturationDetector:
    return SaturationDetector(metrics=get_metrics_registry())

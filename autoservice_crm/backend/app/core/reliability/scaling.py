from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any

from app.core.jobs import get_job_queue
from app.core.prometheus_metrics import PrometheusMetricsRegistry, get_metrics_registry


@dataclass(frozen=True)
class ScalingSignals:
    queue_depth: int
    worker_lag_seconds: float
    request_rate_rps: float
    p95_latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_depth": self.queue_depth,
            "worker_lag_seconds": self.worker_lag_seconds,
            "request_rate_rps": self.request_rate_rps,
            "p95_latency_ms": self.p95_latency_ms,
        }


class AutoScalingSignalExporter:
    """Exports stable autoscaling signals for orchestration systems."""

    def __init__(self, metrics: PrometheusMetricsRegistry) -> None:
        self._metrics = metrics
        self._lock = Lock()
        self._last_requests = 0.0
        self._last_ts = time.time()

    async def collect(self) -> ScalingSignals:
        snapshot = self._metrics.snapshot()
        queue = get_job_queue()
        try:
            queue_depth = int(await queue.size())
        except Exception:
            queue_depth = 0

        worker_lag = self._metrics.histogram_quantile(
            snapshot=snapshot,
            histogram_name="job_queue_delay_seconds",
            quantile=0.95,
        )
        p95_latency = self._metrics.histogram_quantile(
            snapshot=snapshot,
            histogram_name="http_request_duration_seconds",
            quantile=0.95,
        ) * 1000.0
        request_rate = self._compute_request_rate(snapshot)

        self._metrics.set_gauge("autoscaling_queue_depth", queue_depth)
        self._metrics.set_gauge("autoscaling_worker_lag_seconds", worker_lag)
        self._metrics.set_gauge("autoscaling_request_rate_rps", request_rate)
        self._metrics.set_gauge("autoscaling_p95_latency_ms", p95_latency)

        return ScalingSignals(
            queue_depth=queue_depth,
            worker_lag_seconds=worker_lag,
            request_rate_rps=request_rate,
            p95_latency_ms=p95_latency,
        )

    def _compute_request_rate(self, snapshot: dict[str, Any]) -> float:
        total_requests = 0.0
        for row in snapshot.get("counters", []):
            if row.get("name") == "http_requests_total":
                total_requests += float(row.get("value", 0.0))

        now = time.time()
        with self._lock:
            elapsed = max(1e-6, now - self._last_ts)
            delta = max(0.0, total_requests - self._last_requests)
            self._last_requests = total_requests
            self._last_ts = now
            return delta / elapsed


@lru_cache(maxsize=1)
def get_scaling_signal_exporter() -> AutoScalingSignalExporter:
    return AutoScalingSignalExporter(metrics=get_metrics_registry())

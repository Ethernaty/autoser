from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from starlette.requests import Request

from app.core.prometheus_metrics import PrometheusMetricsRegistry, get_metrics_registry


@dataclass
class TraceContext:
    trace_id: str
    started_at: float


@lru_cache(maxsize=1)
def get_observability_registry() -> PrometheusMetricsRegistry:
    return get_metrics_registry()


def start_trace(request: Request) -> TraceContext:
    state_correlation_id = getattr(request.state, "correlation_id", None)
    state_trace_id = getattr(request.state, "trace_id", None)
    trace_id = (
        request.headers.get("X-Trace-ID")
        or state_trace_id
        or state_correlation_id
        or request.headers.get("X-Correlation-ID")
        or str(uuid4())
    )
    return TraceContext(trace_id=trace_id, started_at=time.perf_counter())


def end_trace(trace: TraceContext) -> float:
    return time.perf_counter() - trace.started_at

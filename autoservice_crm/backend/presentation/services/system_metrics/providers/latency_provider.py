from __future__ import annotations

from app.core.prometheus_metrics import get_metrics_registry
from presentation.services.system_metrics.providers.base import MetricReading, SystemMetricsProvider


class RequestLatencyMetricsProvider(SystemMetricsProvider):
    name = "latency"

    async def collect(self) -> list[MetricReading]:
        try:
            registry = get_metrics_registry()
            snapshot = registry.snapshot()
            has_samples = _has_histogram_samples(snapshot=snapshot, histogram_name="http_request_duration_seconds")
            if not has_samples:
                return [
                    MetricReading(
                        key="request_latency",
                        title="Request Latency",
                        value=None,
                        formatted_value="n/a",
                        subtitle="p95 HTTP latency",
                        unit="ms",
                        status="warning",
                    )
                ]

            p95_seconds = registry.histogram_quantile(
                snapshot=snapshot,
                histogram_name="http_request_duration_seconds",
                quantile=0.95,
            )
            p95_ms = max(0.0, float(p95_seconds) * 1000.0)
            return [
                MetricReading(
                    key="request_latency",
                    title="Request Latency",
                    value=p95_ms,
                    formatted_value=_format_latency(p95_ms),
                    subtitle="p95 HTTP latency",
                    unit="ms",
                    status=_latency_status(p95_ms),
                )
            ]
        except Exception:
            return [
                MetricReading(
                    key="request_latency",
                    title="Request Latency",
                    value=None,
                    formatted_value="n/a",
                    subtitle="p95 HTTP latency",
                    unit="ms",
                    status="warning",
                )
            ]


def _has_histogram_samples(*, snapshot: dict[str, object], histogram_name: str) -> bool:
    histograms = snapshot.get("histograms", [])
    if not isinstance(histograms, list):
        return False

    for item in histograms:
        if not isinstance(item, dict):
            continue
        if item.get("name") != histogram_name:
            continue
        try:
            return float(item.get("count", 0.0)) > 0.0
        except Exception:
            return False
    return False


def _format_latency(value_ms: float) -> str:
    if value_ms >= 1_000:
        return f"{value_ms / 1_000:.2f} s"
    return f"{value_ms:.0f} ms"


def _latency_status(value_ms: float) -> str:
    if value_ms >= 1_000:
        return "critical"
    if value_ms >= 500:
        return "warning"
    return "ok"

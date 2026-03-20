from __future__ import annotations

import asyncio
import math
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Sequence

from presentation.services.system_metrics.providers import (
    DatabasePoolMetricsProvider,
    MetricReading,
    QueueMetricsProvider,
    RequestLatencyMetricsProvider,
    RuntimeMetricsProvider,
    SystemMetricsProvider,
)


@dataclass(frozen=True)
class SystemMetricWidgetView:
    key: str
    title: str
    value: str
    subtitle: str
    status: str
    chart_svg: str


@dataclass(frozen=True)
class SystemMetricsDashboardView:
    widgets: list[SystemMetricWidgetView]
    refreshed_at: datetime
    auto_refresh: bool


class SystemMetricsService:
    """Presentation-facing orchestrator for pluggable system metric providers."""

    _METRIC_ORDER = [
        "cpu",
        "ram",
        "active_workers",
        "queue_size",
        "request_latency",
        "uptime",
        "db_connections",
    ]

    def __init__(self, *, providers: Sequence[SystemMetricsProvider], history_limit: int = 40) -> None:
        self._providers = tuple(providers)
        self._history_limit = max(5, history_limit)
        self._history: dict[str, deque[float]] = {}
        self._history_lock = asyncio.Lock()
        self._order_index = {key: idx for idx, key in enumerate(self._METRIC_ORDER)}

    async def build_dashboard_view(self, *, auto_refresh: bool) -> SystemMetricsDashboardView:
        readings = await self._collect_readings()
        ordered_readings = sorted(
            readings,
            key=lambda item: self._order_index.get(item.key, len(self._order_index) + 1),
        )

        widgets: list[SystemMetricWidgetView] = []
        async with self._history_lock:
            for reading in ordered_readings:
                points = self._append_and_snapshot_history(reading)
                widgets.append(
                    SystemMetricWidgetView(
                        key=reading.key,
                        title=reading.title,
                        value=reading.formatted_value,
                        subtitle=reading.subtitle,
                        status=_normalize_status(reading.status),
                        chart_svg=_render_sparkline(points=points),
                    )
                )

        return SystemMetricsDashboardView(
            widgets=widgets,
            refreshed_at=datetime.now(UTC),
            auto_refresh=auto_refresh,
        )

    async def _collect_readings(self) -> list[MetricReading]:
        if not self._providers:
            return []

        results = await asyncio.gather(
            *(provider.collect() for provider in self._providers),
            return_exceptions=True,
        )

        readings: list[MetricReading] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            readings.extend(result)
        return readings

    def _append_and_snapshot_history(self, reading: MetricReading) -> list[float]:
        history = self._history.setdefault(reading.key, deque(maxlen=self._history_limit))

        numeric_value = _coerce_numeric(reading.value)
        if numeric_value is not None:
            history.append(numeric_value)

        return list(history)


@lru_cache(maxsize=1)
def get_system_metrics_service() -> SystemMetricsService:
    return SystemMetricsService(
        providers=(
            RuntimeMetricsProvider(),
            QueueMetricsProvider(),
            RequestLatencyMetricsProvider(),
            DatabasePoolMetricsProvider(),
        )
    )


def _coerce_numeric(value: float | int | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"ok", "warning", "critical"}:
        return normalized
    if normalized in {"error", "down"}:
        return "critical"
    return "ok"


def _render_sparkline(*, points: list[float], width: int = 196, height: int = 52) -> str:
    if not points:
        return (
            '<svg viewBox="0 0 196 52" role="img" aria-label="No data chart">'
            '<rect x="0" y="0" width="196" height="52" rx="8" fill="#f8fafc"></rect>'
            '<text x="98" y="30" text-anchor="middle" fill="#64748b" font-size="10">n/a</text>'
            "</svg>"
        )

    values = points[-24:]
    if len(values) == 1:
        values = [values[0], values[0]]

    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        max_value = min_value + 1.0

    span = max_value - min_value
    x_step = width / (len(values) - 1)

    coordinates: list[tuple[float, float]] = []
    for idx, value in enumerate(values):
        x = idx * x_step
        y = height - (((value - min_value) / span) * (height - 10) + 5)
        coordinates.append((x, y))

    path = " ".join(
        f"{'M' if idx == 0 else 'L'}{x:.2f},{y:.2f}"
        for idx, (x, y) in enumerate(coordinates)
    )
    area_path = f"{path} L{width:.2f},{height:.2f} L0,{height:.2f} Z"

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Metric trend chart">'
        f'<path d="{area_path}" fill="#dbeafe" opacity="0.45"></path>'
        f'<path d="{path}" fill="none" stroke="#1d4ed8" stroke-width="2" stroke-linecap="round"></path>'
        "</svg>"
    )

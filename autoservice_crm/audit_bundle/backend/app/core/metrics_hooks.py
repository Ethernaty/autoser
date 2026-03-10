from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.prometheus_metrics import get_metrics_registry


class MetricsHook(ABC):
    """Pluggable metrics hook interface."""

    @abstractmethod
    async def increment(self, metric: str, value: int = 1, *, tags: dict[str, str] | None = None) -> None:
        ...

    @abstractmethod
    async def histogram(self, metric: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        ...

    @abstractmethod
    async def snapshot(self) -> dict[str, Any]:
        ...


class PrometheusMetricsHook(MetricsHook):
    """Adapter from legacy hook API to Prometheus registry."""

    async def increment(self, metric: str, value: int = 1, *, tags: dict[str, str] | None = None) -> None:
        get_metrics_registry().increment_counter(metric, value=value, labels=tags)

    async def histogram(self, metric: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        get_metrics_registry().observe_histogram(metric, value=value, labels=tags)

    async def snapshot(self) -> dict[str, Any]:
        return {
            "prometheus_text": get_metrics_registry().render_prometheus(),
        }


@lru_cache(maxsize=1)
def get_metrics_hook() -> MetricsHook:
    return PrometheusMetricsHook()

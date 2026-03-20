from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Iterable


_DEFAULT_REQUEST_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_DEFAULT_DB_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
_DEFAULT_REDIS_BUCKETS = (0.001, 0.003, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25)


@dataclass(frozen=True)
class _MetricKey:
    name: str
    labels: tuple[tuple[str, str], ...]


class PrometheusMetricsRegistry:
    """Thread-safe in-process Prometheus metrics registry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[_MetricKey, float] = defaultdict(float)
        self._gauges: dict[_MetricKey, float] = defaultdict(float)
        self._histograms: dict[_MetricKey, dict[str, float]] = {}

    def increment_counter(self, name: str, value: float = 1.0, *, labels: dict[str, str] | None = None) -> None:
        key = _MetricKey(name=name, labels=self._normalize_labels(labels))
        with self._lock:
            self._counters[key] += float(value)

    async def increment_counter_async(self, name: str, value: float = 1.0, *, labels: dict[str, str] | None = None) -> None:
        self.increment_counter(name=name, value=value, labels=labels)

    def set_gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        key = _MetricKey(name=name, labels=self._normalize_labels(labels))
        with self._lock:
            self._gauges[key] = float(value)

    def observe_histogram(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
        buckets: Iterable[float] = _DEFAULT_REQUEST_BUCKETS,
    ) -> None:
        normalized_labels = self._normalize_labels(labels)
        with self._lock:
            histogram = self._histograms.get(_MetricKey(name=name, labels=normalized_labels))
            if histogram is None:
                histogram = self._build_histogram_template(buckets)
                self._histograms[_MetricKey(name=name, labels=normalized_labels)] = histogram

            v = float(value)
            for boundary in tuple(sorted(float(item) for item in buckets)):
                if v <= boundary:
                    histogram[self._bucket_label(boundary)] += 1.0
            histogram["+Inf"] += 1.0
            histogram["sum"] += v
            histogram["count"] += 1.0

    async def observe_histogram_async(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
        buckets: Iterable[float] = _DEFAULT_REQUEST_BUCKETS,
    ) -> None:
        self.observe_histogram(name=name, value=value, labels=labels, buckets=buckets)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            emitted_types: set[str] = set()
            for key, value in sorted(self._counters.items(), key=lambda item: (item[0].name, item[0].labels)):
                if key.name not in emitted_types:
                    lines.append(f"# TYPE {key.name} counter")
                    emitted_types.add(key.name)
                lines.append(f"{key.name}{self._labels_to_string(key.labels)} {value}")

            for key, value in sorted(self._gauges.items(), key=lambda item: (item[0].name, item[0].labels)):
                if key.name not in emitted_types:
                    lines.append(f"# TYPE {key.name} gauge")
                    emitted_types.add(key.name)
                lines.append(f"{key.name}{self._labels_to_string(key.labels)} {value}")

            for key, histogram in sorted(self._histograms.items(), key=lambda item: (item[0].name, item[0].labels)):
                if key.name not in emitted_types:
                    lines.append(f"# TYPE {key.name} histogram")
                    emitted_types.add(key.name)
                for bucket, count in histogram.items():
                    if bucket in {"sum", "count"}:
                        continue
                    labels = dict(key.labels)
                    labels["le"] = bucket
                    lines.append(f"{key.name}_bucket{self._labels_to_string(tuple(sorted(labels.items())))} {count}")
                lines.append(f"{key.name}_sum{self._labels_to_string(key.labels)} {histogram['sum']}")
                lines.append(f"{key.name}_count{self._labels_to_string(key.labels)} {histogram['count']}")

        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        with self._lock:
            counters = [
                {"name": key.name, "labels": dict(key.labels), "value": value}
                for key, value in self._counters.items()
            ]
            gauges = [
                {"name": key.name, "labels": dict(key.labels), "value": value}
                for key, value in self._gauges.items()
            ]
            histograms: list[dict[str, object]] = []
            for key, histogram in self._histograms.items():
                buckets = {k: v for k, v in histogram.items() if k not in {"sum", "count"}}
                histograms.append(
                    {
                        "name": key.name,
                        "labels": dict(key.labels),
                        "buckets": buckets,
                        "sum": float(histogram.get("sum", 0.0)),
                        "count": float(histogram.get("count", 0.0)),
                    }
                )
        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
        }

    def histogram_quantile(self, *, snapshot: dict[str, object], histogram_name: str, quantile: float) -> float:
        q = max(0.0, min(1.0, float(quantile)))
        merged: dict[float, float] = {}
        count_total = 0.0

        for item in snapshot.get("histograms", []):  # type: ignore[union-attr]
            if not isinstance(item, dict):
                continue
            if item.get("name") != histogram_name:
                continue
            buckets = item.get("buckets", {})
            if not isinstance(buckets, dict):
                continue
            for raw_bucket, raw_value in buckets.items():
                if raw_bucket == "+Inf":
                    continue
                try:
                    boundary = float(raw_bucket)
                    value = float(raw_value)
                except Exception:
                    continue
                merged[boundary] = merged.get(boundary, 0.0) + value
            try:
                count_total += float(item.get("count", 0.0))
            except Exception:
                continue

        if count_total <= 0 or not merged:
            return 0.0

        target = count_total * q
        for boundary in sorted(merged):
            if merged[boundary] >= target:
                return boundary
        return max(merged)

    def observe_request(self, *, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        labels = {
            "method": method.upper(),
            "route": route,
            "status_code": str(status_code),
        }
        self.increment_counter("http_requests_total", labels=labels)
        self.observe_histogram(
            "http_request_duration_seconds",
            duration_seconds,
            labels={"method": method.upper(), "route": route},
            buckets=_DEFAULT_REQUEST_BUCKETS,
        )
        if status_code >= 400:
            self.increment_counter("http_errors_total", labels={"method": method.upper(), "route": route})

    def observe_db_query(self, *, statement: str, duration_seconds: float) -> None:
        stmt = statement.strip().split(" ", 1)[0].upper() if statement else "UNKNOWN"
        self.observe_histogram(
            "db_query_duration_seconds",
            duration_seconds,
            labels={"statement": stmt},
            buckets=_DEFAULT_DB_BUCKETS,
        )

    def observe_redis_latency(self, *, operation: str, duration_seconds: float, success: bool) -> None:
        self.observe_histogram(
            "redis_operation_duration_seconds",
            duration_seconds,
            labels={"operation": operation.lower()},
            buckets=_DEFAULT_REDIS_BUCKETS,
        )
        if not success:
            self.increment_counter("redis_operation_errors_total", labels={"operation": operation.lower()})

    def increment_rate_limit_rejection(self, *, route: str, identifier_type: str) -> None:
        self.increment_counter(
            "rate_limit_rejections_total",
            labels={"route": route, "identifier_type": identifier_type},
        )

    def increment_app_error(self, *, source: str, code: str) -> None:
        self.increment_counter("app_errors_total", labels={"source": source, "code": code})

    @staticmethod
    def _build_histogram_template(buckets: Iterable[float]) -> dict[str, float]:
        template = {PrometheusMetricsRegistry._bucket_label(bucket): 0.0 for bucket in sorted(float(item) for item in buckets)}
        template["+Inf"] = 0.0
        template["sum"] = 0.0
        template["count"] = 0.0
        return template

    @staticmethod
    def _bucket_label(value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return format(value, "g")

    @staticmethod
    def _normalize_labels(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    @staticmethod
    def _labels_to_string(labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        parts = []
        for key, value in labels:
            escaped = value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
            parts.append(f'{key}="{escaped}"')
        return "{" + ",".join(parts) + "}"


@lru_cache(maxsize=1)
def get_metrics_registry() -> PrometheusMetricsRegistry:
    return PrometheusMetricsRegistry()


def safe_metric_call(callback, *args, **kwargs) -> None:
    try:
        callback(*args, **kwargs)
    except Exception:
        return


async def safe_metric_call_async(callback, *args, **kwargs) -> None:
    try:
        result = callback(*args, **kwargs)
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        return

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.prometheus_metrics import PrometheusMetricsRegistry, get_metrics_registry


@dataclass(frozen=True)
class SLOTarget:
    name: str
    target: float
    window_seconds: int


@dataclass(frozen=True)
class SLOStatus:
    name: str
    objective: float
    current: float
    compliant: bool
    burn_rate: float
    error_budget_remaining: float
    alert: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "objective": self.objective,
            "current": self.current,
            "compliant": self.compliant,
            "burn_rate": self.burn_rate,
            "error_budget_remaining": self.error_budget_remaining,
            "alert": self.alert,
        }


class SLOMonitor:
    """SLO evaluator with burn-rate and error-budget calculations."""

    def __init__(self, metrics: PrometheusMetricsRegistry) -> None:
        self._metrics = metrics
        settings = get_settings()
        self._latency_target_ms = float(settings.slo_latency_p95_ms)
        self._error_rate_target = float(settings.slo_error_rate_target)
        self._queue_delay_target_ms = float(settings.slo_queue_delay_p95_ms)
        self._webhook_success_target = float(settings.slo_webhook_success_target)
        self._window_seconds = max(60, int(settings.slo_window_seconds))
        self._budget_lock = Lock()
        self._last_update_ts = time.time()
        self._budget_remaining = 1.0

    def evaluate(self) -> dict[str, Any]:
        snapshot = self._metrics.snapshot()
        statuses = [
            self._latency_slo(snapshot),
            self._error_rate_slo(snapshot),
            self._queue_delay_slo(snapshot),
            self._webhook_delivery_slo(snapshot),
        ]

        min_budget = min(item.error_budget_remaining for item in statuses)
        overall = "ok"
        if any(not item.compliant and item.alert == "critical" for item in statuses):
            overall = "critical"
        elif any(not item.compliant for item in statuses):
            overall = "warning"

        return {
            "status": overall,
            "window_seconds": self._window_seconds,
            "slos": [item.to_dict() for item in statuses],
            "error_budget_remaining": min_budget,
        }

    def _latency_slo(self, snapshot: dict[str, Any]) -> SLOStatus:
        current_p95_ms = self._metrics.histogram_quantile(
            snapshot=snapshot,
            histogram_name="http_request_duration_seconds",
            quantile=0.95,
        ) * 1000.0
        objective = self._latency_target_ms
        compliant = current_p95_ms <= objective
        burn_rate = (current_p95_ms / objective) if objective > 0 else 0.0
        budget_remaining = self._consume_budget(burn_rate=burn_rate, compliant=compliant)
        return SLOStatus(
            name="latency_p95_ms",
            objective=objective,
            current=current_p95_ms,
            compliant=compliant,
            burn_rate=burn_rate,
            error_budget_remaining=budget_remaining,
            alert=self._alert_level(compliant=compliant, burn_rate=burn_rate),
        )

    def _error_rate_slo(self, snapshot: dict[str, Any]) -> SLOStatus:
        request_total = self._sum_counters(snapshot=snapshot, metric_name="http_requests_total")
        error_total = self._sum_counters(snapshot=snapshot, metric_name="http_errors_total")
        current_rate = (error_total / request_total) if request_total > 0 else 0.0
        objective = self._error_rate_target
        compliant = current_rate <= objective
        burn_rate = (current_rate / objective) if objective > 0 else 0.0
        budget_remaining = self._consume_budget(burn_rate=burn_rate, compliant=compliant)
        return SLOStatus(
            name="error_rate",
            objective=objective,
            current=current_rate,
            compliant=compliant,
            burn_rate=burn_rate,
            error_budget_remaining=budget_remaining,
            alert=self._alert_level(compliant=compliant, burn_rate=burn_rate),
        )

    def _queue_delay_slo(self, snapshot: dict[str, Any]) -> SLOStatus:
        current_p95_ms = self._metrics.histogram_quantile(
            snapshot=snapshot,
            histogram_name="job_queue_delay_seconds",
            quantile=0.95,
        ) * 1000.0
        objective = self._queue_delay_target_ms
        compliant = current_p95_ms <= objective
        burn_rate = (current_p95_ms / objective) if objective > 0 else 0.0
        budget_remaining = self._consume_budget(burn_rate=burn_rate, compliant=compliant)
        return SLOStatus(
            name="queue_delay_p95_ms",
            objective=objective,
            current=current_p95_ms,
            compliant=compliant,
            burn_rate=burn_rate,
            error_budget_remaining=budget_remaining,
            alert=self._alert_level(compliant=compliant, burn_rate=burn_rate),
        )

    def _webhook_delivery_slo(self, snapshot: dict[str, Any]) -> SLOStatus:
        success = self._sum_counters(
            snapshot=snapshot,
            metric_name="webhook_deliveries_total",
            label_filters={"status": "success"},
        )
        all_deliveries = self._sum_counters(snapshot=snapshot, metric_name="webhook_deliveries_total")
        current = (success / all_deliveries) if all_deliveries > 0 else 1.0
        objective = self._webhook_success_target
        compliant = current >= objective
        burn_rate = ((1.0 - current) / (1.0 - objective)) if objective < 1.0 else 0.0
        budget_remaining = self._consume_budget(burn_rate=burn_rate, compliant=compliant)
        return SLOStatus(
            name="webhook_success_rate",
            objective=objective,
            current=current,
            compliant=compliant,
            burn_rate=burn_rate,
            error_budget_remaining=budget_remaining,
            alert=self._alert_level(compliant=compliant, burn_rate=burn_rate),
        )

    def _sum_counters(
        self,
        *,
        snapshot: dict[str, Any],
        metric_name: str,
        label_filters: dict[str, str] | None = None,
    ) -> float:
        label_filters = label_filters or {}
        total = 0.0
        for row in snapshot.get("counters", []):
            if row.get("name") != metric_name:
                continue
            labels = row.get("labels", {})
            if any(str(labels.get(k)) != str(v) for k, v in label_filters.items()):
                continue
            total += float(row.get("value", 0.0))
        return total

    def _consume_budget(self, *, burn_rate: float, compliant: bool) -> float:
        now = time.time()
        with self._budget_lock:
            elapsed = max(0.0, now - self._last_update_ts)
            self._last_update_ts = now
            if compliant:
                replenish = elapsed / float(self._window_seconds)
                self._budget_remaining = min(1.0, self._budget_remaining + replenish)
            else:
                drain = (elapsed / float(self._window_seconds)) * max(1.0, burn_rate)
                self._budget_remaining = max(0.0, self._budget_remaining - drain)
            return self._budget_remaining

    @staticmethod
    def _alert_level(*, compliant: bool, burn_rate: float) -> str:
        if compliant:
            return "none"
        if burn_rate >= 5.0:
            return "critical"
        if burn_rate >= 2.0:
            return "high"
        return "warning"


@lru_cache(maxsize=1)
def get_slo_monitor() -> SLOMonitor:
    return SLOMonitor(metrics=get_metrics_registry())

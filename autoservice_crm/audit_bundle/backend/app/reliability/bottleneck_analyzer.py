from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BottleneckAnalysis:
    limiting_layer: str
    confidence: float
    scores: dict[str, float]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "limiting_layer": self.limiting_layer,
            "confidence": self.confidence,
            "scores": self.scores,
            "diagnostics": self.diagnostics,
        }


class BottleneckAnalyzer:
    """Heuristic bottleneck analyzer for certification runs."""

    LAYERS = ("cpu", "db", "network", "lock", "cache", "queue")

    def analyze(
        self,
        *,
        stress_result: dict[str, Any],
        saturation_report: dict[str, Any],
        recovery_report: dict[str, Any] | None = None,
    ) -> BottleneckAnalysis:
        signals = ((saturation_report.get("report") or {}).get("signals") or {}) if isinstance(saturation_report, dict) else {}
        queue_depth = float((saturation_report.get("report") or {}).get("queue_depth", 0.0)) if isinstance(saturation_report, dict) else 0.0
        saturation_score = float(saturation_report.get("score", 0.0)) if isinstance(saturation_report, dict) else 0.0

        threadpool_value = self._signal_value(signals, "threadpool_saturation")
        db_pool_value = self._signal_value(signals, "db_pool_exhaustion")
        lock_value = self._signal_value(signals, "lock_contention_storm")
        queue_growth = self._signal_value(signals, "queue_backlog_growth")
        event_loop_lag = self._signal_value(signals, "event_loop_lag")

        p95 = float(stress_result.get("p95_latency_ms", 0.0))
        p99 = float(stress_result.get("p99_latency_ms", 0.0))
        error_rate = float(stress_result.get("error_rate", 0.0))

        scores = {
            "cpu": min(1.0, (event_loop_lag / 250.0) + (threadpool_value / 250.0) + (p99 / 3000.0)),
            "db": min(1.0, db_pool_value + (p95 / 2000.0) + (error_rate * 3.0)),
            "network": min(1.0, (p99 / 2500.0) + (error_rate * 1.5)),
            "lock": min(1.0, (lock_value / 10.0) + (error_rate * 2.0)),
            "cache": min(1.0, (saturation_score * 0.5) + (error_rate * 1.2)),
            "queue": min(1.0, (queue_growth / 50.0) + (queue_depth / 10_000.0)),
        }

        if recovery_report:
            mttr = float(recovery_report.get("mttr_seconds", 0.0))
            peak_error = float(recovery_report.get("peak_error_rate", 0.0))
            scores["queue"] = min(1.0, scores["queue"] + (mttr / 180.0))
            scores["db"] = min(1.0, scores["db"] + peak_error)
            scores["cache"] = min(1.0, scores["cache"] + peak_error * 0.5)

        limiting_layer = max(self.LAYERS, key=lambda layer: scores[layer])
        confidence = float(scores[limiting_layer])
        diagnostics = {
            "saturation_score": saturation_score,
            "signals": signals,
            "stress": {
                "error_rate": error_rate,
                "p95_latency_ms": p95,
                "p99_latency_ms": p99,
                "achieved_rps": float(stress_result.get("achieved_rps", 0.0)),
            },
        }
        if recovery_report:
            diagnostics["recovery"] = {
                "mttr_seconds": float(recovery_report.get("mttr_seconds", 0.0)),
                "peak_error_rate": float(recovery_report.get("peak_error_rate", 0.0)),
            }

        return BottleneckAnalysis(
            limiting_layer=limiting_layer,
            confidence=confidence,
            scores=scores,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _signal_value(signals: dict[str, Any], name: str) -> float:
        value = signals.get(name, {})
        if isinstance(value, dict):
            return float(value.get("value", 0.0))
        return 0.0

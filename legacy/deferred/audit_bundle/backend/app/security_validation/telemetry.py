from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any

from app.security_validation.attack_simulator import AttackSimulationReport


@dataclass(frozen=True)
class TelemetrySnapshot:
    captured_at_unix: float
    attack_traces: list[dict[str, Any]]
    failed_auth_patterns: list[dict[str, Any]]
    anomalous_traffic: dict[str, Any]
    timing_anomalies: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at_unix": self.captured_at_unix,
            "attack_traces": self.attack_traces,
            "failed_auth_patterns": self.failed_auth_patterns,
            "anomalous_traffic": self.anomalous_traffic,
            "timing_anomalies": self.timing_anomalies,
        }


class AttackTelemetryCollector:
    """Collects attack traces and anomaly indicators from validation runs."""

    def __init__(self, *, max_traces: int = 1_000) -> None:
        self._max_traces = max(100, int(max_traces))
        self._traces: deque[dict[str, Any]] = deque(maxlen=self._max_traces)
        self._auth_failures: Counter[str] = Counter()
        self._lock = Lock()

    def ingest(self, report: AttackSimulationReport) -> None:
        with self._lock:
            for result in report.results:
                for trace in result.traces:
                    event = dict(trace)
                    event["ingested_at_unix"] = time.time()
                    self._traces.append(event)

                    status_code = int(trace.get("status_code", 0))
                    if status_code in {401, 403}:
                        self._auth_failures[result.attack] += 1

    def snapshot(self) -> TelemetrySnapshot:
        with self._lock:
            traces = list(self._traces)
            auth_patterns = [
                {"attack": attack, "count": count}
                for attack, count in self._auth_failures.most_common(20)
            ]

        latencies = [float(item.get("latency_ms", 0.0)) for item in traces]
        p95 = self._percentile(latencies, 0.95)
        p99 = self._percentile(latencies, 0.99)
        anomaly_count = sum(1 for value in latencies if value > max(500.0, p95 * 1.8))

        status_histogram: Counter[int] = Counter(int(item.get("status_code", 0)) for item in traces)
        error_ratio = 0.0
        if traces:
            error_ratio = sum(count for code, count in status_histogram.items() if code >= 400) / len(traces)

        return TelemetrySnapshot(
            captured_at_unix=time.time(),
            attack_traces=traces[-200:],
            failed_auth_patterns=auth_patterns,
            anomalous_traffic={
                "total_traces": len(traces),
                "error_ratio": round(error_ratio, 6),
                "status_histogram": {str(k): v for k, v in status_histogram.items()},
            },
            timing_anomalies={
                "p95_latency_ms": round(p95, 3),
                "p99_latency_ms": round(p99, 3),
                "anomaly_count": int(anomaly_count),
            },
        )

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = int(max(0, min(len(ordered) - 1, round((len(ordered) - 1) * q))))
        return float(ordered[idx])


@lru_cache(maxsize=1)
def get_attack_telemetry_collector() -> AttackTelemetryCollector:
    return AttackTelemetryCollector()

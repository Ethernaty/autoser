from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapacityEstimate:
    max_tenants: int
    max_rps: float
    max_concurrent_users: int
    safe_scaling_thresholds: dict[str, float]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tenants": self.max_tenants,
            "max_rps": self.max_rps,
            "max_concurrent_users": self.max_concurrent_users,
            "safe_scaling_thresholds": self.safe_scaling_thresholds,
            "recommendations": self.recommendations,
        }


class CapacityEstimator:
    """Estimate safe capacity from certification run outputs."""

    def estimate(
        self,
        *,
        stress_result: dict[str, Any],
        saturation_report: dict[str, Any],
        bottleneck_analysis: dict[str, Any],
        observed_tenants: int,
        observed_concurrent_users: int,
    ) -> CapacityEstimate:
        observed_rps = max(0.1, float(stress_result.get("achieved_rps", 0.0)))
        saturation_score = float(saturation_report.get("score", 0.0))
        saturation_score = max(0.05, min(1.0, saturation_score))

        growth_factor = min(5.0, max(1.0, 1.0 / saturation_score))
        max_rps = observed_rps * growth_factor

        max_tenants = max(1, int(observed_tenants * growth_factor))
        max_users = max(1, int(observed_concurrent_users * growth_factor))

        queue_depth = float((saturation_report.get("report") or {}).get("queue_depth", 0.0))
        p95_ms = float(stress_result.get("p95_latency_ms", 0.0))
        error_rate = float(stress_result.get("error_rate", 0.0))

        thresholds = {
            "scale_out_rps": round(max_rps * 0.7, 3),
            "scale_out_queue_depth": max(100.0, queue_depth * 0.7 + 50.0),
            "scale_out_p95_latency_ms": max(200.0, p95_ms * 0.8),
            "scale_out_error_rate": max(0.005, error_rate * 1.2),
        }

        limiting_layer = str(bottleneck_analysis.get("limiting_layer", "unknown"))
        recommendations = [
            f"prioritize_{limiting_layer}_scaling",
            "enable_proactive_scale_out_at_70_percent_thresholds",
            "reserve_30_percent_headroom_for_failure_recovery",
        ]

        return CapacityEstimate(
            max_tenants=max_tenants,
            max_rps=round(max_rps, 3),
            max_concurrent_users=max_users,
            safe_scaling_thresholds=thresholds,
            recommendations=recommendations,
        )

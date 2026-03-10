from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from app.reliability.bottleneck_analyzer import BottleneckAnalyzer
from app.reliability.capacity_estimator import CapacityEstimator
from app.reliability.failure_recovery_profiler import FailureRecoveryProfiler, RecoveryProfileConfig
from app.reliability.stress_test_runner import LoadProfile, StressTestConfig, StressTestRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Production certification runner for distributed SaaS backend")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument(
        "--profile",
        default="mixed",
        choices=[member.value for member in LoadProfile],
        help="Stress profile",
    )
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--base-rps", type=float, default=100.0)
    parser.add_argument("--peak-rps", type=float, default=500.0)
    parser.add_argument("--tenants", type=int, default=10)
    parser.add_argument("--concurrent-users", type=int, default=100)
    parser.add_argument("--request-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--auth-token", action="append", default=[])
    parser.add_argument("--internal-auth-header", default="X-Internal-Service-Auth")
    parser.add_argument("--internal-auth-key", default="")
    parser.add_argument("--skip-recovery", action="store_true")
    return parser


def _json_print(title: str, payload: dict[str, Any]) -> None:
    print(title)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), indent=2))


async def _run(args: argparse.Namespace) -> int:
    stress_config = StressTestConfig(
        base_url=str(args.base_url).rstrip("/"),
        profile=LoadProfile(str(args.profile)),
        duration_seconds=max(1, int(args.duration_seconds)),
        base_rps=max(1.0, float(args.base_rps)),
        peak_rps=max(1.0, float(args.peak_rps)),
        tenants=max(1, int(args.tenants)),
        concurrent_workers=max(1, int(args.concurrent_users)),
        request_timeout_seconds=max(0.5, float(args.request_timeout_seconds)),
        auth_tokens=tuple(str(token) for token in args.auth_token if str(token).strip()),
        internal_auth_header=str(args.internal_auth_header) if str(args.internal_auth_header).strip() else None,
        internal_auth_key=str(args.internal_auth_key) if str(args.internal_auth_key).strip() else None,
    )
    stress_runner = StressTestRunner(stress_config)
    stress_result = await stress_runner.run()
    saturation_report = stress_result.saturation_signals

    recovery_report: dict[str, Any] = {}
    if not args.skip_recovery and str(args.internal_auth_key).strip():
        recovery_profiler = FailureRecoveryProfiler(
            RecoveryProfileConfig(
                base_url=str(args.base_url).rstrip("/"),
                internal_auth_header=str(args.internal_auth_header),
                internal_auth_key=str(args.internal_auth_key),
                request_timeout_seconds=max(0.5, float(args.request_timeout_seconds)),
            )
        )
        recovery_report = (await recovery_profiler.run()).to_dict()

    bottleneck = BottleneckAnalyzer().analyze(
        stress_result=stress_result.to_dict(),
        saturation_report=saturation_report,
        recovery_report=recovery_report if recovery_report else None,
    )
    capacity = CapacityEstimator().estimate(
        stress_result=stress_result.to_dict(),
        saturation_report=saturation_report,
        bottleneck_analysis=bottleneck.to_dict(),
        observed_tenants=max(1, int(args.tenants)),
        observed_concurrent_users=max(1, int(args.concurrent_users)),
    )

    certification_result = {
        "stress": stress_result.to_dict(),
        "recovery": recovery_report,
    }
    bottleneck_analysis = bottleneck.to_dict()
    safe_limits = capacity.to_dict()
    scaling_recommendations = {
        "recommendations": safe_limits.get("recommendations", []),
        "safe_scaling_thresholds": safe_limits.get("safe_scaling_thresholds", {}),
    }

    _json_print("CERTIFICATION RESULT", certification_result)
    _json_print("BOTTLENECK ANALYSIS", bottleneck_analysis)
    _json_print("SAFE LIMITS", safe_limits)
    _json_print("SCALING RECOMMENDATIONS", scaling_recommendations)
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class FailureScenario:
    name: str
    chaos_patch: dict[str, Any]


@dataclass(frozen=True)
class RecoveryProfileConfig:
    base_url: str
    internal_auth_header: str
    internal_auth_key: str
    probe_path: str = "/health/ready"
    probe_interval_seconds: float = 0.5
    baseline_window_seconds: int = 5
    failure_window_seconds: int = 8
    recovery_timeout_seconds: int = 60
    acceptable_error_rate: float = 0.02
    acceptable_latency_multiplier: float = 1.5
    request_timeout_seconds: float = 5.0


@dataclass
class ScenarioRecoveryResult:
    scenario: str
    mttr_seconds: float
    degradation_duration_seconds: float
    peak_error_rate: float
    baseline_p95_ms: float
    failure_p95_ms: float
    recovered: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "mttr_seconds": self.mttr_seconds,
            "degradation_duration_seconds": self.degradation_duration_seconds,
            "peak_error_rate": self.peak_error_rate,
            "baseline_p95_ms": self.baseline_p95_ms,
            "failure_p95_ms": self.failure_p95_ms,
            "recovered": self.recovered,
        }


@dataclass
class FailureRecoveryReport:
    mttr_seconds: float
    degradation_duration_seconds: float
    peak_error_rate: float
    scenarios: list[ScenarioRecoveryResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mttr_seconds": self.mttr_seconds,
            "degradation_duration_seconds": self.degradation_duration_seconds,
            "peak_error_rate": self.peak_error_rate,
            "scenarios": [item.to_dict() for item in self.scenarios],
        }


@dataclass
class _ProbeWindow:
    requests: int
    errors: int
    peak_error_rate: float
    p95_latency_ms: float

    @property
    def error_rate(self) -> float:
        if self.requests <= 0:
            return 0.0
        return self.errors / self.requests


class FailureRecoveryProfiler:
    """Profiles system recovery after induced infrastructure failures."""

    def __init__(self, config: RecoveryProfileConfig) -> None:
        self._config = config
        self._scenarios = (
            FailureScenario(name="redis_outage", chaos_patch={"enabled": True, "redis_failure_rate": 1.0}),
            FailureScenario(name="db_failover", chaos_patch={"enabled": True, "db_latency_ms": 1500}),
            FailureScenario(name="queue_stall", chaos_patch={"enabled": True, "queue_delay_ms": 2500}),
            FailureScenario(name="lock_contention_storm", chaos_patch={"enabled": True, "exception_rate": 0.15}),
        )

    async def run(self) -> FailureRecoveryReport:
        timeout = httpx.Timeout(timeout=self._config.request_timeout_seconds)
        async with httpx.AsyncClient(base_url=self._config.base_url.rstrip("/"), timeout=timeout) as client:
            scenario_results: list[ScenarioRecoveryResult] = []
            for scenario in self._scenarios:
                result = await self._run_scenario(client=client, scenario=scenario)
                scenario_results.append(result)

        if not scenario_results:
            return FailureRecoveryReport(mttr_seconds=0.0, degradation_duration_seconds=0.0, peak_error_rate=0.0, scenarios=[])

        mttr = sum(item.mttr_seconds for item in scenario_results) / len(scenario_results)
        degradation = sum(item.degradation_duration_seconds for item in scenario_results) / len(scenario_results)
        peak_error = max(item.peak_error_rate for item in scenario_results)
        return FailureRecoveryReport(
            mttr_seconds=mttr,
            degradation_duration_seconds=degradation,
            peak_error_rate=peak_error,
            scenarios=scenario_results,
        )

    async def _run_scenario(self, *, client: httpx.AsyncClient, scenario: FailureScenario) -> ScenarioRecoveryResult:
        baseline = await self._probe_window(client=client, duration_seconds=self._config.baseline_window_seconds)
        await self._set_chaos_policy(client=client, updates=scenario.chaos_patch)

        failure_window = await self._probe_window(client=client, duration_seconds=self._config.failure_window_seconds)
        await self._reset_chaos(client=client)

        recovered, mttr = await self._wait_for_recovery(client=client, baseline=baseline)
        degradation = float(self._config.failure_window_seconds) + mttr
        return ScenarioRecoveryResult(
            scenario=scenario.name,
            mttr_seconds=mttr,
            degradation_duration_seconds=degradation,
            peak_error_rate=failure_window.peak_error_rate,
            baseline_p95_ms=baseline.p95_latency_ms,
            failure_p95_ms=failure_window.p95_latency_ms,
            recovered=recovered,
        )

    async def _probe_window(self, *, client: httpx.AsyncClient, duration_seconds: int) -> _ProbeWindow:
        end_at = time.perf_counter() + max(1, int(duration_seconds))
        latencies: list[float] = []
        requests = 0
        errors = 0
        peak_error_rate = 0.0
        while time.perf_counter() < end_at:
            requests += 1
            started = time.perf_counter()
            try:
                response = await client.get(self._config.probe_path)
                if response.status_code >= 400:
                    errors += 1
            except Exception:
                errors += 1
            latency_ms = (time.perf_counter() - started) * 1000.0
            latencies.append(latency_ms)
            peak_error_rate = max(peak_error_rate, errors / max(1, requests))
            await asyncio.sleep(max(0.01, self._config.probe_interval_seconds))

        p95 = self._percentile(latencies, 0.95)
        return _ProbeWindow(
            requests=requests,
            errors=errors,
            peak_error_rate=peak_error_rate,
            p95_latency_ms=p95,
        )

    async def _wait_for_recovery(self, *, client: httpx.AsyncClient, baseline: _ProbeWindow) -> tuple[bool, float]:
        started = time.perf_counter()
        target_latency = max(1.0, baseline.p95_latency_ms * self._config.acceptable_latency_multiplier)
        timeout_at = started + max(1, self._config.recovery_timeout_seconds)
        while time.perf_counter() < timeout_at:
            window = await self._probe_window(client=client, duration_seconds=2)
            if window.error_rate <= self._config.acceptable_error_rate and window.p95_latency_ms <= target_latency:
                return True, max(0.0, time.perf_counter() - started)
        return False, max(0.0, time.perf_counter() - started)

    async def _set_chaos_policy(self, *, client: httpx.AsyncClient, updates: dict[str, Any]) -> None:
        headers = {self._config.internal_auth_header: self._config.internal_auth_key}
        payload = {"enabled": True, **updates}
        try:
            await client.post("/internal/chaos/policy", headers=headers, json=payload)
        except Exception:
            return

    async def _reset_chaos(self, *, client: httpx.AsyncClient) -> None:
        headers = {self._config.internal_auth_header: self._config.internal_auth_key}
        try:
            await client.post("/internal/chaos/reset", headers=headers)
        except Exception:
            return

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = int(max(0, min(len(ordered) - 1, round((len(ordered) - 1) * q))))
        return float(ordered[idx])

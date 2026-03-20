from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx


class LoadProfile(str, Enum):
    sustained = "sustained"
    spike = "spike"
    staircase = "staircase"
    tenant_isolated = "tenant_isolated"
    mixed = "mixed"


@dataclass(frozen=True)
class StressPhase:
    name: str
    rate_rps: float
    duration_seconds: int


@dataclass(frozen=True)
class StressTestConfig:
    base_url: str
    profile: LoadProfile
    duration_seconds: int = 60
    base_rps: float = 100.0
    peak_rps: float = 500.0
    tenants: int = 10
    concurrent_workers: int = 100
    request_timeout_seconds: float = 5.0
    request_paths: tuple[str, ...] = ("/health", "/health/ready", "/clients?limit=10&offset=0")
    auth_tokens: tuple[str, ...] = ()
    internal_auth_header: str | None = None
    internal_auth_key: str | None = None
    max_latency_samples: int = 200_000


@dataclass
class StressTestResult:
    profile: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    achieved_rps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    saturation_signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "duration_seconds": self.duration_seconds,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": self.error_rate,
            "achieved_rps": self.achieved_rps,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "saturation_signals": self.saturation_signals,
        }


class _ReservoirLatency:
    def __init__(self, max_samples: int) -> None:
        self._max_samples = max(1, int(max_samples))
        self._samples: list[float] = []
        self._seen = 0
        self._rng = random.Random()

    def add(self, value_ms: float) -> None:
        self._seen += 1
        if len(self._samples) < self._max_samples:
            self._samples.append(float(value_ms))
            return
        idx = self._rng.randint(0, self._seen - 1)
        if idx < self._max_samples:
            self._samples[idx] = float(value_ms)

    def percentile(self, q: float) -> float:
        if not self._samples:
            return 0.0
        ordered = sorted(self._samples)
        index = int(max(0, min(len(ordered) - 1, round((len(ordered) - 1) * q))))
        return float(ordered[index])


class StressTestRunner:
    """Certification stress runner for sustained/spike/staircase/mixed workloads."""

    def __init__(self, config: StressTestConfig) -> None:
        self._config = config
        self._latency = _ReservoirLatency(max_samples=config.max_latency_samples)
        self._total_requests = 0
        self._failed_requests = 0
        self._success_requests = 0

    async def run(self) -> StressTestResult:
        phases = self._build_phases()
        started = time.perf_counter()
        timeout = httpx.Timeout(timeout=self._config.request_timeout_seconds)
        limits = httpx.Limits(max_connections=max(32, self._config.concurrent_workers * 2), max_keepalive_connections=max(16, self._config.concurrent_workers))
        async with httpx.AsyncClient(base_url=self._config.base_url.rstrip("/"), timeout=timeout, limits=limits) as client:
            for phase in phases:
                await self._run_phase(client=client, phase=phase)
            saturation = await self._fetch_saturation(client=client)

        elapsed = max(1e-6, time.perf_counter() - started)
        return StressTestResult(
            profile=self._config.profile.value,
            duration_seconds=elapsed,
            total_requests=self._total_requests,
            successful_requests=self._success_requests,
            failed_requests=self._failed_requests,
            error_rate=(self._failed_requests / self._total_requests) if self._total_requests else 0.0,
            achieved_rps=self._total_requests / elapsed,
            p50_latency_ms=self._latency.percentile(0.50),
            p95_latency_ms=self._latency.percentile(0.95),
            p99_latency_ms=self._latency.percentile(0.99),
            saturation_signals=saturation,
        )

    async def _run_phase(self, *, client: httpx.AsyncClient, phase: StressPhase) -> None:
        rate = max(1.0, float(phase.rate_rps))
        duration = max(1, int(phase.duration_seconds))
        queue: asyncio.Queue[tuple[str, dict[str, str]]] = asyncio.Queue(maxsize=max(1_000, self._config.concurrent_workers * 50))
        workers = [asyncio.create_task(self._worker(client=client, queue=queue)) for _ in range(max(1, self._config.concurrent_workers))]
        scheduled = 0
        try:
            phase_end = time.perf_counter() + duration
            next_emit = time.perf_counter()
            while time.perf_counter() < phase_end:
                tenant_idx = scheduled % max(1, self._config.tenants)
                path = self._pick_path(tenant_idx=tenant_idx)
                headers = self._build_headers(tenant_idx=tenant_idx)
                await queue.put((path, headers))
                scheduled += 1
                next_emit += 1.0 / rate
                await asyncio.sleep(max(0.0, next_emit - time.perf_counter()))
            await queue.join()
        finally:
            for _ in workers:
                await queue.put(("", {}))
            await asyncio.gather(*workers, return_exceptions=True)

    async def _worker(self, *, client: httpx.AsyncClient, queue: asyncio.Queue[tuple[str, dict[str, str]]]) -> None:
        while True:
            path, headers = await queue.get()
            if not path:
                queue.task_done()
                return
            started = time.perf_counter()
            ok = False
            try:
                response = await client.get(path, headers=headers)
                ok = response.status_code < 500
            except Exception:
                ok = False
            finally:
                latency_ms = (time.perf_counter() - started) * 1000.0
                self._latency.add(latency_ms)
                self._total_requests += 1
                if ok:
                    self._success_requests += 1
                else:
                    self._failed_requests += 1
                queue.task_done()

    def _build_headers(self, *, tenant_idx: int) -> dict[str, str]:
        token = self._pick_token(tenant_idx=tenant_idx)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def _pick_path(self, *, tenant_idx: int) -> str:
        paths = self._config.request_paths
        if not paths:
            return "/health"
        if self._config.profile is LoadProfile.tenant_isolated:
            return paths[tenant_idx % len(paths)]
        return random.choice(paths)

    def _pick_token(self, *, tenant_idx: int) -> str | None:
        tokens = self._config.auth_tokens
        if not tokens:
            return None
        if self._config.profile is LoadProfile.tenant_isolated:
            return tokens[tenant_idx % len(tokens)]
        return random.choice(tokens)

    async def _fetch_saturation(self, *, client: httpx.AsyncClient) -> dict[str, Any]:
        if not self._config.internal_auth_header or not self._config.internal_auth_key:
            return {}
        try:
            response = await client.get(
                "/internal/saturation-report",
                headers={self._config.internal_auth_header: self._config.internal_auth_key},
            )
            if response.status_code >= 400:
                return {}
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _build_phases(self) -> list[StressPhase]:
        total = max(1, int(self._config.duration_seconds))
        base = max(1.0, float(self._config.base_rps))
        peak = max(base, float(self._config.peak_rps))

        if self._config.profile is LoadProfile.sustained:
            return [StressPhase(name="sustained", rate_rps=base, duration_seconds=total)]

        if self._config.profile is LoadProfile.spike:
            low_1 = max(1, int(total * 0.4))
            spike = max(1, int(total * 0.2))
            low_2 = max(1, total - low_1 - spike)
            return [
                StressPhase(name="warmup", rate_rps=base, duration_seconds=low_1),
                StressPhase(name="spike", rate_rps=peak, duration_seconds=spike),
                StressPhase(name="cooldown", rate_rps=base, duration_seconds=low_2),
            ]

        if self._config.profile is LoadProfile.staircase:
            steps = 5
            per = max(1, total // steps)
            phases: list[StressPhase] = []
            for idx in range(steps):
                ratio = (idx + 1) / steps
                phases.append(
                    StressPhase(
                        name=f"step_{idx + 1}",
                        rate_rps=base + (peak - base) * ratio,
                        duration_seconds=per,
                    )
                )
            remainder = total - per * steps
            if remainder > 0:
                phases[-1] = StressPhase(
                    name=phases[-1].name,
                    rate_rps=phases[-1].rate_rps,
                    duration_seconds=phases[-1].duration_seconds + remainder,
                )
            return phases

        if self._config.profile is LoadProfile.tenant_isolated:
            return [StressPhase(name="tenant_isolated", rate_rps=base, duration_seconds=total)]

        mixed_segments = max(5, total // 10)
        phases = []
        for idx in range(mixed_segments):
            ratio = random.uniform(0.4, 1.0)
            rate = base + (peak - base) * ratio
            phases.append(StressPhase(name=f"mixed_{idx + 1}", rate_rps=rate, duration_seconds=max(1, total // mixed_segments)))
        used = sum(phase.duration_seconds for phase in phases)
        if used < total:
            phases[-1] = StressPhase(
                name=phases[-1].name,
                rate_rps=phases[-1].rate_rps,
                duration_seconds=phases[-1].duration_seconds + (total - used),
            )
        return phases

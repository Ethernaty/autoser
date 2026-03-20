from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.security_validation.attack_simulator import AttackSimulationReport, AttackSimulator, AttackSimulatorConfig
from app.security_validation.exploit_runner import ExploitRunner
from app.security_validation.security_scanner import SecurityScannerEngine
from app.security_validation.security_score_engine import SecurityScoreEngine, remediation_plan
from app.security_validation.telemetry import get_attack_telemetry_collector


@dataclass(frozen=True)
class SecurityValidationOutput:
    attack_results: dict[str, Any]
    vulnerabilities: dict[str, Any]
    risk_score: dict[str, Any]
    exploit_paths: dict[str, Any]
    remediation: list[dict[str, Any]]
    telemetry: dict[str, Any]
    generated_at_unix: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_results": self.attack_results,
            "vulnerabilities": self.vulnerabilities,
            "risk_score": self.risk_score,
            "exploit_paths": self.exploit_paths,
            "remediation": self.remediation,
            "telemetry": self.telemetry,
            "generated_at_unix": self.generated_at_unix,
        }


class SecurityValidationService:
    """Runs attack simulation and produces a security report snapshot."""

    def __init__(self) -> None:
        self._scan_engine = SecurityScannerEngine()
        self._exploit_runner = ExploitRunner()
        self._score_engine = SecurityScoreEngine()
        self._telemetry = get_attack_telemetry_collector()
        self._lock = asyncio.Lock()
        self._last_report: SecurityValidationOutput | None = None

    async def get_or_run(
        self,
        *,
        base_url: str,
        jwt_tokens: tuple[str, ...],
        api_keys: tuple[str, ...],
        force_refresh: bool,
    ) -> SecurityValidationOutput:
        async with self._lock:
            if self._last_report is not None and not force_refresh:
                return self._last_report
            output = await self._run(
                base_url=base_url,
                jwt_tokens=jwt_tokens,
                api_keys=api_keys,
            )
            self._last_report = output
            return output

    async def _run(
        self,
        *,
        base_url: str,
        jwt_tokens: tuple[str, ...],
        api_keys: tuple[str, ...],
    ) -> SecurityValidationOutput:
        attack_report: AttackSimulationReport = await AttackSimulator(
            AttackSimulatorConfig(
                base_url=base_url,
                jwt_tokens=jwt_tokens,
                api_keys=api_keys,
            )
        ).run()
        self._telemetry.ingest(attack_report)

        scan = self._scan_engine.scan(attack_report)
        exploit = self._exploit_runner.run(scan)
        score = self._score_engine.calculate(scan=scan, exploit=exploit)
        telemetry_snapshot = self._telemetry.snapshot()
        remediation = remediation_plan(scan)

        return SecurityValidationOutput(
            attack_results=attack_report.to_dict(),
            vulnerabilities=scan.to_dict(),
            risk_score=score.to_dict(),
            exploit_paths=exploit.to_dict(),
            remediation=remediation,
            telemetry=telemetry_snapshot.to_dict(),
            generated_at_unix=time.time(),
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.security_validation.exploit_runner import ExploitRunnerReport
from app.security_validation.security_scanner import SecurityScannerReport


@dataclass(frozen=True)
class SecurityScoreReport:
    security_score: float
    risk_level: str
    exploitability_index: float
    blast_radius: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_score": self.security_score,
            "risk_level": self.risk_level,
            "exploitability_index": self.exploitability_index,
            "blast_radius": self.blast_radius,
        }


class SecurityScoreEngine:
    """Calculates a 0-100 security score and risk profile."""

    _SEVERITY_PENALTY = {
        "critical": 28.0,
        "high": 16.0,
        "medium": 8.0,
        "low": 3.0,
    }

    def calculate(self, *, scan: SecurityScannerReport, exploit: ExploitRunnerReport) -> SecurityScoreReport:
        score = 100.0
        has_tenant_breakout = False
        has_auth_bypass = False

        for vuln in scan.vulnerabilities:
            severity = vuln.severity.lower()
            penalty = self._SEVERITY_PENALTY.get(severity, 4.0) * max(0.25, float(vuln.confidence))
            score -= penalty
            if vuln.id == "cross_tenant_data_exposure":
                has_tenant_breakout = True
            if vuln.id in {"auth_bypass", "privilege_escalation"}:
                has_auth_bypass = True

        score -= exploit.attack_surface_score * 0.15
        score = max(0.0, min(100.0, score))

        exploitability = min(1.0, max(0.0, exploit.exploit_success_probability))
        if score >= 85:
            risk = "low"
        elif score >= 70:
            risk = "moderate"
        elif score >= 50:
            risk = "high"
        else:
            risk = "critical"

        blast = "service"
        if has_tenant_breakout or has_auth_bypass:
            blast = "multi_tenant"
        if has_tenant_breakout and has_auth_bypass:
            blast = "platform_wide"

        return SecurityScoreReport(
            security_score=round(score, 3),
            risk_level=risk,
            exploitability_index=round(exploitability, 6),
            blast_radius=blast,
        )


def remediation_plan(scan: SecurityScannerReport) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ordered = sorted(
        scan.vulnerabilities,
        key=lambda item: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item.severity.lower(), 4),
    )
    for vuln in ordered:
        items.append(
            {
                "id": vuln.id,
                "priority": vuln.severity.lower(),
                "action": vuln.remediation,
            }
        )
    if not items:
        items.append({"id": "none", "priority": "none", "action": "No critical findings detected."})
    return items

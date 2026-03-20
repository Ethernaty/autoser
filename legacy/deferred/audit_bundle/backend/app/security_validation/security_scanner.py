from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.security_validation.attack_simulator import AttackSimulationReport, AttackResult


@dataclass(frozen=True)
class VulnerabilityFinding:
    id: str
    title: str
    category: str
    severity: str
    confidence: float
    evidence: dict[str, Any]
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class SecurityScannerReport:
    vulnerabilities: list[VulnerabilityFinding]
    detection_matrix: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vulnerabilities": [item.to_dict() for item in self.vulnerabilities],
            "detection_matrix": self.detection_matrix,
        }


class SecurityScannerEngine:
    """Converts attack simulation outcomes into vulnerability findings."""

    def scan(self, report: AttackSimulationReport) -> SecurityScannerReport:
        by_attack = {item.attack: item for item in report.results}
        vulnerabilities: list[VulnerabilityFinding] = []
        matrix: dict[str, dict[str, Any]] = {}

        def add_detection(key: str, attack: str, *, title: str, category: str, severity: str, remediation: str) -> None:
            result = by_attack.get(attack)
            detected = bool(result and result.vulnerable)
            confidence = float(result.success_probability if result else 0.0)
            evidence = (result.evidence if result else {"reason": "attack_not_executed"})
            matrix[key] = {
                "detected": detected,
                "attack": attack,
                "confidence": confidence,
                "evidence": evidence,
            }
            if detected:
                vulnerabilities.append(
                    VulnerabilityFinding(
                        id=key,
                        title=title,
                        category=category,
                        severity=severity,
                        confidence=confidence,
                        evidence=evidence,
                        remediation=remediation,
                    )
                )

        add_detection(
            "auth_bypass",
            "jwt_tampering",
            title="Authentication bypass via tampered JWT",
            category="authentication",
            severity="critical",
            remediation="Enforce strict JWT signature verification and reject malformed/tampered tokens.",
        )
        add_detection(
            "privilege_escalation",
            "header_spoofing",
            title="Privilege escalation via header spoofing",
            category="authorization",
            severity="high",
            remediation="Ignore untrusted privilege headers and enforce internal auth boundary at gateway layer.",
        )
        add_detection(
            "cross_tenant_data_exposure",
            "tenant_breakout_attempts",
            title="Cross-tenant data exposure",
            category="tenant_isolation",
            severity="critical",
            remediation="Enforce tenant scoping in repository/service/cache and reject tenant hints from clients.",
        )
        add_detection(
            "idempotency_abuse",
            "replay_attacks",
            title="Replay/idempotency abuse",
            category="consistency",
            severity="high",
            remediation="Bind idempotency key to request hash and actor scope; reject mismatched replays.",
        )
        add_detection(
            "dos_vectors",
            "payload_bombs",
            title="Payload bomb DoS vector",
            category="availability",
            severity="high",
            remediation="Reject oversized payloads at ingress and enforce depth/size limits before parsing.",
        )
        add_detection(
            "queue_injection",
            "webhook_signature_forgery",
            title="Queue injection through webhook forgery",
            category="integrity",
            severity="high",
            remediation="Require authenticated publisher identity and verify signing scheme for event ingestion.",
        )
        add_detection(
            "lock_bypass",
            "race_condition_exploits",
            title="Lock/consistency bypass via race condition",
            category="concurrency",
            severity="high",
            remediation="Enforce unique constraints and transactional conflict handling with deterministic retries.",
        )
        add_detection(
            "cache_poisoning",
            "tenant_breakout_attempts",
            title="Potential cache poisoning across tenant boundaries",
            category="cache_safety",
            severity="medium",
            remediation="Validate tenant_id on cache reads and purge mismatched objects.",
        )
        add_detection(
            "rate_limit_bypass",
            "rate_limit_bypass_attempts",
            title="Rate limiter bypass",
            category="abuse_protection",
            severity="medium",
            remediation="Bind limiter keys to authenticated principal and trusted proxy chain only.",
        )
        add_detection(
            "api_key_bruteforce",
            "api_key_bruteforce",
            title="API key brute-force acceptance",
            category="authentication",
            severity="high",
            remediation="Enforce constant-time key checks, progressive delays, and anomaly-triggered lockouts.",
        )

        return SecurityScannerReport(vulnerabilities=vulnerabilities, detection_matrix=matrix)

    @staticmethod
    def find_attack(report: AttackSimulationReport, name: str) -> AttackResult | None:
        for item in report.results:
            if item.attack == name:
                return item
        return None

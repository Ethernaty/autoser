from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import random
import string
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.security_validation.http_client import HttpResponse, SimpleHttpClient


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


@dataclass(frozen=True)
class AttackSimulatorConfig:
    base_url: str
    jwt_tokens: tuple[str, ...] = ()
    api_keys: tuple[str, ...] = ()
    timeout_seconds: float = 5.0
    race_parallelism: int = 10
    brute_force_attempts: int = 40
    rate_limit_attempts: int = 140


@dataclass(frozen=True)
class AttackResult:
    attack: str
    status: str
    vulnerable: bool
    success_probability: float
    evidence: dict[str, Any]
    latency_ms: float
    traces: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack": self.attack,
            "status": self.status,
            "vulnerable": self.vulnerable,
            "success_probability": self.success_probability,
            "evidence": self.evidence,
            "latency_ms": self.latency_ms,
            "traces": self.traces,
        }


@dataclass(frozen=True)
class AttackSimulationReport:
    started_at_unix: float
    duration_seconds: float
    results: list[AttackResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at_unix": self.started_at_unix,
            "duration_seconds": self.duration_seconds,
            "results": [item.to_dict() for item in self.results],
        }


class AttackSimulator:
    """Adversarial attack simulator for control-plane security validation."""

    def __init__(self, config: AttackSimulatorConfig) -> None:
        self._config = config
        self._client = SimpleHttpClient(base_url=config.base_url, timeout_seconds=config.timeout_seconds)

    async def run(self) -> AttackSimulationReport:
        started = time.time()
        tasks = [
            self._jwt_tampering(),
            self._api_key_bruteforce(),
            self._rate_limit_bypass_attempts(),
            self._tenant_breakout_attempts(),
            self._replay_attacks(),
            self._webhook_signature_forgery(),
            self._payload_bombs(),
            self._header_spoofing(),
            self._race_condition_exploits(),
        ]
        results = await asyncio.gather(*tasks)
        duration = max(0.0, time.time() - started)
        return AttackSimulationReport(
            started_at_unix=started,
            duration_seconds=duration,
            results=list(results),
        )

    async def _jwt_tampering(self) -> AttackResult:
        started = time.perf_counter()
        token = self._config.jwt_tokens[0] if self._config.jwt_tokens else None
        if token is None:
            return self._skipped("jwt_tampering", "missing_jwt_token", started)

        tampered = self._tamper_jwt(token)
        response = await asyncio.to_thread(
            self._client.request,
            method="GET",
            path="/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        vulnerable = response.status_code < 400
        return AttackResult(
            attack="jwt_tampering",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={"status_code": response.status_code},
            latency_ms=response.latency_ms,
            traces=[self._trace("jwt_tampering", response)],
        )

    async def _api_key_bruteforce(self) -> AttackResult:
        started = time.perf_counter()
        traces: list[dict[str, Any]] = []
        success = 0
        attempts = max(1, int(self._config.brute_force_attempts))
        for _ in range(attempts):
            fake_key = "sk_" + "".join(random.choices(string.ascii_letters + string.digits, k=48))
            response = await asyncio.to_thread(
                self._client.request,
                method="GET",
                path="/external/v1/clients?limit=1&offset=0",
                headers={"Authorization": f"Bearer {fake_key}"},
            )
            if response.status_code < 400:
                success += 1
            if len(traces) < 12:
                traces.append(self._trace("api_key_bruteforce", response))

        vulnerable = success > 0
        probability = success / attempts
        return AttackResult(
            attack="api_key_bruteforce",
            status="completed",
            vulnerable=vulnerable,
            success_probability=probability,
            evidence={"attempts": attempts, "successful_attempts": success},
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=traces,
        )

    async def _rate_limit_bypass_attempts(self) -> AttackResult:
        started = time.perf_counter()
        token = self._config.jwt_tokens[0] if self._config.jwt_tokens else None
        if token is None:
            return self._skipped("rate_limit_bypass_attempts", "missing_jwt_token", started)

        attempts = max(1, int(self._config.rate_limit_attempts))
        status_counts: dict[int, int] = {}
        traces: list[dict[str, Any]] = []
        for idx in range(attempts):
            spoofed_ip = f"203.0.113.{(idx % 250) + 1}"
            response = await asyncio.to_thread(
                self._client.request,
                method="GET",
                path="/clients?limit=1&offset=0",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-For": spoofed_ip,
                },
            )
            status_counts[response.status_code] = status_counts.get(response.status_code, 0) + 1
            if len(traces) < 15:
                traces.append(self._trace("rate_limit_bypass_attempts", response))

        limited = any(code == 429 for code in status_counts)
        vulnerable = not limited and attempts >= 120
        return AttackResult(
            attack="rate_limit_bypass_attempts",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={"attempts": attempts, "status_counts": status_counts},
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=traces,
        )

    async def _tenant_breakout_attempts(self) -> AttackResult:
        started = time.perf_counter()
        if len(self._config.jwt_tokens) < 2:
            return self._skipped("tenant_breakout_attempts", "requires_two_jwt_tokens", started)

        token_a, token_b = self._config.jwt_tokens[0], self._config.jwt_tokens[1]
        me_a = await asyncio.to_thread(
            self._client.request,
            method="GET",
            path="/auth/me",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        me_b = await asyncio.to_thread(
            self._client.request,
            method="GET",
            path="/auth/me",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        tenant_a = self._extract_tenant_id(me_a)
        tenant_b = self._extract_tenant_id(me_b)
        if tenant_a is None or tenant_b is None:
            return self._skipped("tenant_breakout_attempts", "unable_to_resolve_tenants", started)

        list_resp = await asyncio.to_thread(
            self._client.request,
            method="GET",
            path="/clients?limit=20&offset=0",
            headers={
                "Authorization": f"Bearer {token_a}",
                "X-Tenant-Id": tenant_b,
            },
        )
        leaked = self._contains_tenant_id(list_resp.json_body, tenant_b)
        vulnerable = leaked
        return AttackResult(
            attack="tenant_breakout_attempts",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={
                "tenant_a": tenant_a,
                "tenant_b": tenant_b,
                "status_code": list_resp.status_code,
                "cross_tenant_records_detected": leaked,
            },
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=[
                self._trace("tenant_breakout_attempts", me_a),
                self._trace("tenant_breakout_attempts", me_b),
                self._trace("tenant_breakout_attempts", list_resp),
            ],
        )

    async def _replay_attacks(self) -> AttackResult:
        started = time.perf_counter()
        token = self._config.jwt_tokens[0] if self._config.jwt_tokens else None
        if token is None:
            return self._skipped("replay_attacks", "missing_jwt_token", started)

        idem_key = f"security-test-{uuid4()}"
        phone = "79" + "".join(random.choices(string.digits, k=9))
        payload = {"name": "Replay Test", "phone": phone, "email": None, "comment": "attack-sim"}

        first = await asyncio.to_thread(
            self._client.request,
            method="POST",
            path="/clients/",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
            json_payload=payload,
        )
        second = await asyncio.to_thread(
            self._client.request,
            method="POST",
            path="/clients/",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
            json_payload=payload,
        )

        first_id = self._extract_entity_id(first.json_body)
        second_id = self._extract_entity_id(second.json_body)
        vulnerable = (
            first.status_code < 400
            and second.status_code < 400
            and first_id is not None
            and second_id is not None
            and first_id != second_id
        )
        probability = 1.0 if vulnerable else 0.0
        return AttackResult(
            attack="replay_attacks",
            status="completed",
            vulnerable=vulnerable,
            success_probability=probability,
            evidence={
                "first_status": first.status_code,
                "second_status": second.status_code,
                "first_id": first_id,
                "second_id": second_id,
            },
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=[self._trace("replay_attacks", first), self._trace("replay_attacks", second)],
        )

    async def _webhook_signature_forgery(self) -> AttackResult:
        started = time.perf_counter()
        payload = {"event_name": "forged.event", "payload": {"v": 1}}
        response = await asyncio.to_thread(
            self._client.request,
            method="POST",
            path="/webhooks/publish",
            headers={
                "X-Webhook-Signature": "sha256=00000000",
                "X-Webhook-Timestamp": str(int(time.time())),
            },
            json_payload=payload,
        )
        vulnerable = response.status_code < 400
        return AttackResult(
            attack="webhook_signature_forgery",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={"status_code": response.status_code},
            latency_ms=response.latency_ms,
            traces=[self._trace("webhook_signature_forgery", response)],
        )

    async def _payload_bombs(self) -> AttackResult:
        started = time.perf_counter()
        large_field = "A" * (2 * 1024 * 1024)
        payload = {"email": "x@example.com", "password": large_field, "tenant_slug": "x"}
        response = await asyncio.to_thread(
            self._client.request,
            method="POST",
            path="/auth/login",
            json_payload=payload,
        )
        vulnerable = response.status_code < 400
        return AttackResult(
            attack="payload_bombs",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={"status_code": response.status_code, "payload_bytes": len(json.dumps(payload))},
            latency_ms=response.latency_ms,
            traces=[self._trace("payload_bombs", response)],
        )

    async def _header_spoofing(self) -> AttackResult:
        started = time.perf_counter()
        response = await asyncio.to_thread(
            self._client.request,
            method="GET",
            path="/internal/system-health",
            headers={"X-Internal-Service-Auth": "spoofed-value"},
        )
        vulnerable = response.status_code < 400
        return AttackResult(
            attack="header_spoofing",
            status="completed",
            vulnerable=vulnerable,
            success_probability=1.0 if vulnerable else 0.0,
            evidence={"status_code": response.status_code},
            latency_ms=response.latency_ms,
            traces=[self._trace("header_spoofing", response)],
        )

    async def _race_condition_exploits(self) -> AttackResult:
        started = time.perf_counter()
        token = self._config.jwt_tokens[0] if self._config.jwt_tokens else None
        if token is None:
            return self._skipped("race_condition_exploits", "missing_jwt_token", started)

        phone = "79" + "".join(random.choices(string.digits, k=9))
        payload = {"name": "Race Probe", "phone": phone, "email": None, "comment": "race"}

        async def create_once() -> HttpResponse:
            return await asyncio.to_thread(
                self._client.request,
                method="POST",
                path="/clients/",
                headers={"Authorization": f"Bearer {token}"},
                json_payload=payload,
            )

        responses = await asyncio.gather(*[create_once() for _ in range(max(2, self._config.race_parallelism))])
        success_count = sum(1 for item in responses if item.status_code < 400)
        vulnerable = success_count > 1
        traces = [self._trace("race_condition_exploits", item) for item in responses[:12]]
        return AttackResult(
            attack="race_condition_exploits",
            status="completed",
            vulnerable=vulnerable,
            success_probability=min(1.0, success_count / max(1, len(responses))),
            evidence={
                "parallel_requests": len(responses),
                "success_count": success_count,
                "status_codes": [item.status_code for item in responses],
            },
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=traces,
        )

    def _tamper_jwt(self, token: str) -> str:
        parts = token.split(".")
        if len(parts) != 3:
            return token + "x"
        try:
            payload_raw = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
            payload_raw["sub"] = str(uuid4())
            payload_raw["tampered"] = True
            parts[1] = _b64url_encode(json.dumps(payload_raw, separators=(",", ":")).encode("utf-8"))
            return ".".join(parts)
        except Exception:
            return token[:-1] + ("a" if token[-1] != "a" else "b")

    def _extract_tenant_id(self, response: HttpResponse) -> str | None:
        if not isinstance(response.json_body, dict):
            return None
        tenant = response.json_body.get("tenant")
        if isinstance(tenant, dict):
            value = tenant.get("id")
            return str(value) if value else None
        return None

    @staticmethod
    def _extract_entity_id(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("id")
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _contains_tenant_id(payload: Any, tenant_id: str) -> bool:
        if isinstance(payload, dict):
            if str(payload.get("tenant_id")) == str(tenant_id):
                return True
            for value in payload.values():
                if AttackSimulator._contains_tenant_id(value, tenant_id):
                    return True
        elif isinstance(payload, list):
            for item in payload:
                if AttackSimulator._contains_tenant_id(item, tenant_id):
                    return True
        return False

    def _skipped(self, attack: str, reason: str, started: float) -> AttackResult:
        return AttackResult(
            attack=attack,
            status="skipped",
            vulnerable=False,
            success_probability=0.0,
            evidence={"reason": reason},
            latency_ms=(time.perf_counter() - started) * 1000.0,
            traces=[],
        )

    @staticmethod
    def _trace(attack: str, response: HttpResponse) -> dict[str, Any]:
        body_hash = hashlib.sha256(response.text.encode("utf-8", errors="ignore")).hexdigest()
        return {
            "attack": attack,
            "status_code": response.status_code,
            "latency_ms": round(response.latency_ms, 3),
            "body_sha256": body_hash,
        }

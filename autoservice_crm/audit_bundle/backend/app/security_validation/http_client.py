from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    text: str
    json_body: Any
    latency_ms: float


class SimpleHttpClient:
    """Minimal sync HTTP client for internal validation tooling."""

    def __init__(self, *, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = max(0.5, float(timeout_seconds))

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        json_payload: Any = None,
        raw_payload: bytes | None = None,
    ) -> HttpResponse:
        target = f"{self._base_url}{path}" if path.startswith("/") else f"{self._base_url}/{path}"
        payload_bytes: bytes | None = raw_payload
        req_headers = dict(headers or {})

        if json_payload is not None and raw_payload is None:
            payload_bytes = json.dumps(json_payload, separators=(",", ":")).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        request = urllib.request.Request(
            url=target,
            data=payload_bytes,
            headers=req_headers,
            method=method.upper(),
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read()
                status = int(getattr(response, "status", 200))
                headers_out = {k.lower(): v for k, v in dict(response.headers).items()}
        except urllib.error.HTTPError as exc:
            body = exc.read() if exc.fp is not None else b""
            status = int(exc.code)
            headers_out = {k.lower(): v for k, v in dict(exc.headers or {}).items()}
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return HttpResponse(
                status_code=599,
                headers={},
                text=str(exc),
                json_body=None,
                latency_ms=latency_ms,
            )

        latency_ms = (time.perf_counter() - started) * 1000.0
        text = body.decode("utf-8", errors="replace")
        json_body: Any = None
        if text:
            try:
                json_body = json.loads(text)
            except Exception:
                json_body = None

        return HttpResponse(
            status_code=status,
            headers=headers_out,
            text=text,
            json_body=json_body,
            latency_ms=latency_ms,
        )

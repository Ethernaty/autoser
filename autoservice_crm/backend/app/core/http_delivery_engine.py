from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

from app.core.config import get_settings
from app.core.prometheus_metrics import get_metrics_registry


@dataclass(frozen=True)
class HttpDeliveryResult:
    status_code: int | None
    body: str | None
    error: str | None


class HttpDeliveryEngine:
    """Async pooled HTTP engine with retries and backpressure control."""

    RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        max_connections: int,
        max_keepalive_connections: int,
        timeout_seconds: float,
        retries: int,
        concurrency: int,
    ) -> None:
        import httpx

        self._timeout_seconds = max(0.5, timeout_seconds)
        self._retries = max(0, retries)
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._metrics = get_metrics_registry()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds),
            limits=httpx.Limits(
                max_connections=max(10, max_connections),
                max_keepalive_connections=max(1, max_keepalive_connections),
            ),
        )

    async def deliver(
        self,
        *,
        url: str,
        payload: bytes,
        headers: Mapping[str, str],
        method: str = "POST",
    ) -> HttpDeliveryResult:
        async with self._semaphore:
            return await self._deliver_with_retry(url=url, payload=payload, headers=headers, method=method)

    async def close(self) -> None:
        await self._client.aclose()

    async def _deliver_with_retry(
        self,
        *,
        url: str,
        payload: bytes,
        headers: Mapping[str, str],
        method: str,
    ) -> HttpDeliveryResult:
        import httpx

        attempts = self._retries + 1
        for attempt in range(1, attempts + 1):
            started_at = time.perf_counter()
            try:
                response = await self._client.request(
                    method=method.upper(),
                    url=url,
                    content=payload,
                    headers=dict(headers),
                )
                duration = max(0.0, time.perf_counter() - started_at)
                self._metrics.observe_histogram(
                    "external_requests_latency_seconds",
                    duration,
                    labels={"channel": "webhook", "method": method.upper()},
                )
                body = response.text[:2048] if response.text else None
                if response.status_code in self.RETRYABLE_STATUS_CODES and attempt < attempts:
                    await self._sleep_with_jitter(attempt)
                    continue
                return HttpDeliveryResult(status_code=int(response.status_code), body=body, error=None)
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.NetworkError) as exc:
                duration = max(0.0, time.perf_counter() - started_at)
                self._metrics.observe_histogram(
                    "external_requests_latency_seconds",
                    duration,
                    labels={"channel": "webhook", "method": method.upper()},
                )
                if attempt < attempts:
                    await self._sleep_with_jitter(attempt)
                    continue
                return HttpDeliveryResult(status_code=None, body=None, error=str(exc))
            except Exception as exc:
                duration = max(0.0, time.perf_counter() - started_at)
                self._metrics.observe_histogram(
                    "external_requests_latency_seconds",
                    duration,
                    labels={"channel": "webhook", "method": method.upper()},
                )
                return HttpDeliveryResult(status_code=None, body=None, error=str(exc))

        return HttpDeliveryResult(status_code=None, body=None, error="delivery_failed")

    async def _sleep_with_jitter(self, attempt: int) -> None:
        base = 0.05 * (2 ** max(attempt - 1, 0))
        jitter = base * (0.5 + random.random())
        await asyncio.sleep(min(1.0, jitter))


@lru_cache(maxsize=1)
def get_http_delivery_engine() -> HttpDeliveryEngine:
    settings = get_settings()
    return HttpDeliveryEngine(
        max_connections=settings.webhook_http_max_connections,
        max_keepalive_connections=settings.webhook_http_max_keepalive,
        timeout_seconds=settings.webhook_timeout_seconds,
        retries=settings.webhook_internal_http_retries,
        concurrency=settings.webhook_dispatch_concurrency,
    )

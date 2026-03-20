from __future__ import annotations

import argparse
import asyncio
import random
import time
from dataclasses import dataclass
from typing import Iterable

import httpx

from app.core.jobs import get_job_queue


@dataclass(frozen=True)
class LoadConfig:
    base_url: str
    tenants: int
    users_per_tenant: int
    duration_seconds: int
    webhook_burst: int
    queue_spike: int
    request_timeout_seconds: float
    auth_tokens: tuple[str, ...]


@dataclass
class LoadStats:
    requests_total: int = 0
    requests_failed: int = 0
    webhook_requests: int = 0
    queue_jobs_enqueued: int = 0


async def run_load(config: LoadConfig) -> LoadStats:
    stats = LoadStats()
    timeout = httpx.Timeout(config.request_timeout_seconds)
    async with httpx.AsyncClient(base_url=config.base_url, timeout=timeout) as client:
        stop_at = time.time() + config.duration_seconds
        tasks: list[asyncio.Task[None]] = []

        for tenant_idx in range(config.tenants):
            token = _token_for_tenant(config.auth_tokens, tenant_idx)
            for user_idx in range(config.users_per_tenant):
                tasks.append(
                    asyncio.create_task(
                        _simulate_user(
                            client=client,
                            stop_at=stop_at,
                            tenant_idx=tenant_idx,
                            user_idx=user_idx,
                            auth_token=token,
                            stats=stats,
                        )
                    )
                )

        if config.webhook_burst > 0:
            tasks.append(
                asyncio.create_task(
                    _simulate_webhook_bursts(
                        client=client,
                        stop_at=stop_at,
                        per_burst=config.webhook_burst,
                        auth_tokens=config.auth_tokens,
                        stats=stats,
                    )
                )
            )

        if config.queue_spike > 0:
            tasks.append(
                asyncio.create_task(
                    _simulate_queue_spikes(
                        stop_at=stop_at,
                        spike_size=config.queue_spike,
                        stats=stats,
                    )
                )
            )

        await asyncio.gather(*tasks)
    return stats


async def _simulate_user(
    *,
    client: httpx.AsyncClient,
    stop_at: float,
    tenant_idx: int,
    user_idx: int,
    auth_token: str | None,
    stats: LoadStats,
) -> None:
    rng = random.Random(f"{tenant_idx}:{user_idx}")
    while time.time() < stop_at:
        path = "/health" if auth_token is None else rng.choice(["/health", "/clients?limit=10&offset=0"])
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        try:
            response = await client.get(path, headers=headers)
            stats.requests_total += 1
            if response.status_code >= 400:
                stats.requests_failed += 1
        except Exception:
            stats.requests_total += 1
            stats.requests_failed += 1
        await asyncio.sleep(rng.uniform(0.01, 0.2))


async def _simulate_webhook_bursts(
    *,
    client: httpx.AsyncClient,
    stop_at: float,
    per_burst: int,
    auth_tokens: Iterable[str],
    stats: LoadStats,
) -> None:
    token_list = list(auth_tokens)
    if not token_list:
        return

    while time.time() < stop_at:
        burst_tasks: list[asyncio.Task[None]] = []
        for _ in range(per_burst):
            token = random.choice(token_list)
            burst_tasks.append(asyncio.create_task(_publish_webhook_event(client=client, token=token, stats=stats)))
        await asyncio.gather(*burst_tasks)
        await asyncio.sleep(1.0)


async def _publish_webhook_event(*, client: httpx.AsyncClient, token: str, stats: LoadStats) -> None:
    payload = {
        "event_name": "load.simulated",
        "payload": {"origin": "load_simulator", "ts": time.time()},
    }
    try:
        response = await client.post(
            "/webhooks/publish",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        stats.requests_total += 1
        stats.webhook_requests += 1
        if response.status_code >= 400:
            stats.requests_failed += 1
    except Exception:
        stats.requests_total += 1
        stats.webhook_requests += 1
        stats.requests_failed += 1


async def _simulate_queue_spikes(*, stop_at: float, spike_size: int, stats: LoadStats) -> None:
    queue = get_job_queue()
    while time.time() < stop_at:
        for idx in range(spike_size):
            try:
                await queue.enqueue(
                    task_name="load.simulated",
                    payload={"index": idx, "ts": time.time()},
                    max_retries=0,
                    retry_base_delay_seconds=1.0,
                    delay_seconds=0.0,
                )
                stats.queue_jobs_enqueued += 1
            except Exception:
                continue
        await asyncio.sleep(1.0)


def _token_for_tenant(tokens: tuple[str, ...], tenant_idx: int) -> str | None:
    if not tokens:
        return None
    return tokens[tenant_idx % len(tokens)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic load simulator for reliability validation")
    parser.add_argument("--base-url", required=True, help="API base URL, for example http://127.0.0.1:8000")
    parser.add_argument("--tenants", type=int, default=10, help="Number of simulated tenants")
    parser.add_argument("--users-per-tenant", type=int, default=20, help="Concurrent users per tenant")
    parser.add_argument("--duration-seconds", type=int, default=60, help="Simulation duration")
    parser.add_argument("--webhook-burst", type=int, default=0, help="Webhook publish requests per burst")
    parser.add_argument("--queue-spike", type=int, default=0, help="Jobs enqueued per second for queue spike simulation")
    parser.add_argument("--request-timeout-seconds", type=float, default=5.0, help="HTTP request timeout")
    parser.add_argument(
        "--auth-token",
        action="append",
        default=[],
        help="JWT token used for authenticated traffic (can be passed multiple times)",
    )
    return parser


async def _async_main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    config = LoadConfig(
        base_url=str(args.base_url).rstrip("/"),
        tenants=max(1, int(args.tenants)),
        users_per_tenant=max(1, int(args.users_per_tenant)),
        duration_seconds=max(1, int(args.duration_seconds)),
        webhook_burst=max(0, int(args.webhook_burst)),
        queue_spike=max(0, int(args.queue_spike)),
        request_timeout_seconds=max(0.5, float(args.request_timeout_seconds)),
        auth_tokens=tuple(str(token) for token in args.auth_token if str(token).strip()),
    )

    started_at = time.time()
    stats = await run_load(config)
    duration = max(1e-6, time.time() - started_at)
    rps = stats.requests_total / duration
    error_rate = (stats.requests_failed / stats.requests_total) if stats.requests_total else 0.0

    print(
        {
            "duration_seconds": round(duration, 3),
            "requests_total": stats.requests_total,
            "requests_failed": stats.requests_failed,
            "error_rate": round(error_rate, 6),
            "rps": round(rps, 3),
            "webhook_requests": stats.webhook_requests,
            "queue_jobs_enqueued": stats.queue_jobs_enqueued,
        }
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())

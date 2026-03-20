from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.database import check_database_health
from app.core.internal_auth import require_internal_service_auth
from app.core.jobs import get_job_queue
from app.core.prometheus_metrics import get_metrics_registry


router = APIRouter(tags=["Health"])


class DependencyStatus(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float | None = None
    details: dict[str, str] = Field(default_factory=dict)


class HealthDepsResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    checked_at: datetime
    dependencies: dict[str, DependencyStatus]


class HealthReadyResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    checked_at: datetime
    db: Literal["up", "down"]
    redis: Literal["up", "down"]


class HealthLiveResponse(BaseModel):
    status: Literal["ok"]
    checked_at: datetime


async def _check_db() -> DependencyStatus:
    started_at = datetime.now(UTC)
    try:
        await run_in_threadpool(check_database_health)
        latency_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000.0
        return DependencyStatus(status="up", latency_ms=round(latency_ms, 3))
    except Exception as exc:
        return DependencyStatus(status="down", details={"error": str(exc)[:200]})


async def _check_redis() -> DependencyStatus:
    settings = get_settings()
    started_at = datetime.now(UTC)
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        ok = bool(await client.ping())
        await client.aclose()
        latency_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000.0
        return DependencyStatus(status="up" if ok else "down", latency_ms=round(latency_ms, 3))
    except Exception as exc:
        return DependencyStatus(status="down", details={"error": str(exc)[:200]})


async def _check_queue() -> DependencyStatus:
    started_at = datetime.now(UTC)
    try:
        queue = get_job_queue()
        ok = bool(await queue.ping())
        latency_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000.0
        return DependencyStatus(status="up" if ok else "down", latency_ms=round(latency_ms, 3))
    except Exception as exc:
        return DependencyStatus(status="down", details={"error": str(exc)[:200]})


@router.get("/health/live", response_model=HealthLiveResponse)
async def health_live() -> HealthLiveResponse:
    return HealthLiveResponse(status="ok", checked_at=datetime.now(UTC))


@router.get("/health/ready", response_model=HealthReadyResponse)
@router.get("/health", response_model=HealthReadyResponse)
async def health_ready() -> HealthReadyResponse:
    checked_at = datetime.now(UTC)
    db_status = await _check_db()
    redis_status = await _check_redis()

    if db_status.status == "up" and redis_status.status == "up":
        overall = "ok"
    elif db_status.status == "down" and redis_status.status == "down":
        overall = "down"
    else:
        overall = "degraded"

    return HealthReadyResponse(
        status=overall,
        checked_at=checked_at,
        db=db_status.status,
        redis=redis_status.status,
    )


@router.get("/health/deps", response_model=HealthDepsResponse, dependencies=[Depends(require_internal_service_auth)])
async def health_deps() -> HealthDepsResponse:
    checked_at = datetime.now(UTC)
    db_status = await _check_db()
    redis_status = await _check_redis()
    queue_status = await _check_queue()

    dependencies = {
        "db": db_status,
        "redis": redis_status,
        "queue": queue_status,
    }

    down_count = sum(1 for dependency in dependencies.values() if dependency.status == "down")
    if down_count == 0:
        overall = "ok"
    elif down_count == len(dependencies):
        overall = "down"
    else:
        overall = "degraded"

    return HealthDepsResponse(status=overall, checked_at=checked_at, dependencies=dependencies)


@router.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(require_internal_service_auth)])
async def metrics() -> PlainTextResponse:
    payload = get_metrics_registry().render_prometheus()
    return PlainTextResponse(content=payload, media_type="text/plain; version=0.0.4; charset=utf-8")

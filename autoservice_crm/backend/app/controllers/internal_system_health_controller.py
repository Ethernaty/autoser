from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.cache import get_cache_backend
from app.core.database import check_database_health
from app.core.event_stream import get_event_stream_backend
from app.core.internal_auth import require_internal_service_auth
from app.core.jobs import get_job_queue
from app.core.prometheus_metrics import get_metrics_registry
from app.core.reliability.chaos import ChaosPolicy, get_chaos_engine
from app.core.reliability.failover import get_failover_manager
from app.core.reliability.scaling import get_scaling_signal_exporter
from app.core.reliability.slo import get_slo_monitor
from app.reliability.saturation_detector import collect_saturation_snapshot


router = APIRouter(
    prefix="/internal",
    tags=["Internal Reliability"],
    dependencies=[Depends(require_internal_service_auth)],
)


class DependencyHealth(BaseModel):
    status: str
    details: dict[str, str] = Field(default_factory=dict)


class SystemHealthResponse(BaseModel):
    checked_at: datetime
    dependencies: dict[str, DependencyHealth]
    queue_lag_seconds_p95: float
    lock_contention_total: float
    rate_limiter_pressure: float
    cache_hit_ratio: float
    slo_status: dict


class ChaosPolicyUpdateRequest(BaseModel):
    enabled: bool | None = None
    redis_failure_rate: float | None = None
    db_latency_ms: int | None = None
    queue_delay_ms: int | None = None
    event_drop_rate: float | None = None
    exception_rate: float | None = None


class ChaosPolicyResponse(BaseModel):
    policy: dict


class SaturationReportResponse(BaseModel):
    checked_at: datetime
    status: str
    score: float
    report: dict


@router.get("/system-health", response_model=SystemHealthResponse)
async def internal_system_health() -> SystemHealthResponse:
    dependencies = await _collect_dependency_health()
    metrics = get_metrics_registry()
    snapshot = metrics.snapshot()
    scaling = await get_scaling_signal_exporter().collect()
    lock_contention = _sum_counter(snapshot=snapshot, name="distributed_lock_contention_total")
    rate_limiter_pressure = _rate_limiter_pressure(snapshot=snapshot)
    cache_hit_ratio = _cache_hit_ratio(snapshot=snapshot)
    slo_status = get_slo_monitor().evaluate()

    return SystemHealthResponse(
        checked_at=datetime.now(UTC),
        dependencies=dependencies,
        queue_lag_seconds_p95=scaling.worker_lag_seconds,
        lock_contention_total=lock_contention,
        rate_limiter_pressure=rate_limiter_pressure,
        cache_hit_ratio=cache_hit_ratio,
        slo_status=slo_status,
    )


@router.get("/scaling-signals")
async def internal_scaling_signals() -> dict:
    signals = await get_scaling_signal_exporter().collect()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "signals": signals.to_dict(),
    }


@router.get("/slo-status")
async def internal_slo_status() -> dict:
    return get_slo_monitor().evaluate()


@router.get("/chaos/policy", response_model=ChaosPolicyResponse)
async def get_chaos_policy() -> ChaosPolicyResponse:
    policy = get_chaos_engine().get_policy()
    return ChaosPolicyResponse(policy=policy.to_dict())


@router.post("/chaos/policy", response_model=ChaosPolicyResponse)
async def update_chaos_policy(payload: ChaosPolicyUpdateRequest) -> ChaosPolicyResponse:
    updates = payload.model_dump(exclude_none=True)
    policy = get_chaos_engine().set_policy(updates)
    return ChaosPolicyResponse(policy=policy.to_dict())


@router.post("/chaos/reset", response_model=ChaosPolicyResponse)
async def reset_chaos_policy() -> ChaosPolicyResponse:
    policy = get_chaos_engine().reset_policy()
    return ChaosPolicyResponse(policy=policy.to_dict())


@router.get("/failover/status")
async def failover_status() -> dict:
    return await get_failover_manager().status()


@router.get("/saturation-report", response_model=SaturationReportResponse)
async def saturation_report() -> SaturationReportResponse:
    snapshot = await collect_saturation_snapshot()
    return SaturationReportResponse(
        checked_at=snapshot.checked_at,
        status=snapshot.status,
        score=snapshot.score,
        report=snapshot.report,
    )


async def _collect_dependency_health() -> dict[str, DependencyHealth]:
    db = await _check_db()
    cache = await _check_cache()
    queue = await _check_queue()
    stream = await _check_event_stream()
    return {
        "db": db,
        "cache": cache,
        "queue": queue,
        "event_stream": stream,
    }


async def _check_db() -> DependencyHealth:
    try:
        await run_in_threadpool(check_database_health)
        return DependencyHealth(status="up")
    except Exception as exc:
        return DependencyHealth(status="down", details={"error": str(exc)[:200]})


async def _check_cache() -> DependencyHealth:
    cache = get_cache_backend()
    try:
        ok = bool(await cache.ping())
        return DependencyHealth(status="up" if ok else "down")
    except Exception as exc:
        return DependencyHealth(status="down", details={"error": str(exc)[:200]})


async def _check_queue() -> DependencyHealth:
    queue = get_job_queue()
    try:
        ok = bool(await queue.ping())
        size = int(await queue.size())
        return DependencyHealth(status="up" if ok else "down", details={"depth": str(size)})
    except Exception as exc:
        return DependencyHealth(status="down", details={"error": str(exc)[:200]})


async def _check_event_stream() -> DependencyHealth:
    stream = get_event_stream_backend()
    try:
        if hasattr(stream, "_get_producer"):
            producer = await stream._get_producer()  # type: ignore[attr-defined]
            if hasattr(producer, "partitions_for"):
                await producer.partitions_for(getattr(stream, "_topic", ""))
        else:
            await stream.replay(tenant_id=uuid4(), limit=1)
        return DependencyHealth(status="up")
    except Exception as exc:
        return DependencyHealth(status="down", details={"error": str(exc)[:200]})


def _sum_counter(*, snapshot: dict, name: str) -> float:
    total = 0.0
    for row in snapshot.get("counters", []):
        if row.get("name") == name:
            total += float(row.get("value", 0.0))
    return total


def _rate_limiter_pressure(*, snapshot: dict) -> float:
    rejections = _sum_counter(snapshot=snapshot, name="rate_limit_rejections_total")
    requests = _sum_counter(snapshot=snapshot, name="http_requests_total")
    if requests <= 0:
        return 0.0
    return rejections / requests


def _cache_hit_ratio(*, snapshot: dict) -> float:
    hits = _sum_counter(snapshot=snapshot, name="cache_hits_total")
    misses = _sum_counter(snapshot=snapshot, name="cache_misses_total")
    total = hits + misses
    if total <= 0:
        return 1.0
    return hits / total

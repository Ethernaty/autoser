from __future__ import annotations

from presentation.services.system_metrics.providers.base import MetricReading, SystemMetricsProvider


class DatabasePoolMetricsProvider(SystemMetricsProvider):
    name = "database"

    async def collect(self) -> list[MetricReading]:
        pool_size, checked_out = _read_pool_state()
        if checked_out is None and pool_size is None:
            return [
                MetricReading(
                    key="db_connections",
                    title="DB Connections",
                    value=None,
                    formatted_value="n/a",
                    subtitle="Checked out / pool size",
                    unit="ratio",
                    status="warning",
                )
            ]

        if pool_size and pool_size > 0 and checked_out is not None:
            utilization = min(1.0, max(0.0, checked_out / pool_size))
            return [
                MetricReading(
                    key="db_connections",
                    title="DB Connections",
                    value=utilization,
                    formatted_value=f"{checked_out} / {pool_size}",
                    subtitle="Checked out / pool size",
                    unit="ratio",
                    status=_utilization_status(utilization),
                )
            ]

        value = float(checked_out if checked_out is not None else 0)
        label = str(checked_out) if checked_out is not None else str(pool_size)
        return [
            MetricReading(
                key="db_connections",
                title="DB Connections",
                value=value,
                formatted_value=label,
                subtitle="Checked out DB connections",
                unit="count",
                status="warning",
            )
        ]


def _read_pool_state() -> tuple[int | None, int | None]:
    try:
        from app.core.database import engine
    except Exception:
        return None, None

    pool = getattr(engine, "pool", None)
    if pool is None:
        return None, None

    pool_size = _read_int_attr(pool, "size")
    checked_out = _read_int_attr(pool, "checkedout")
    return pool_size, checked_out


def _read_int_attr(target: object, attr: str) -> int | None:
    value = getattr(target, attr, None)
    try:
        if callable(value):
            return int(value())
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _utilization_status(utilization: float) -> str:
    if utilization >= 0.95:
        return "critical"
    if utilization >= 0.8:
        return "warning"
    return "ok"

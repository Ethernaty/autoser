from __future__ import annotations

from app.core.jobs import get_job_queue
from presentation.services.system_metrics.providers.base import MetricReading, SystemMetricsProvider


class QueueMetricsProvider(SystemMetricsProvider):
    name = "queue"

    async def collect(self) -> list[MetricReading]:
        try:
            queue_size = int(await get_job_queue().size())
            return [
                MetricReading(
                    key="queue_size",
                    title="Queue Size",
                    value=queue_size,
                    formatted_value=str(queue_size),
                    subtitle="Pending background jobs",
                    unit="count",
                    status=_queue_status(queue_size),
                )
            ]
        except Exception:
            return [
                MetricReading(
                    key="queue_size",
                    title="Queue Size",
                    value=None,
                    formatted_value="n/a",
                    subtitle="Pending background jobs",
                    unit="count",
                    status="warning",
                )
            ]


def _queue_status(queue_size: int) -> str:
    if queue_size >= 1_000:
        return "critical"
    if queue_size >= 250:
        return "warning"
    return "ok"

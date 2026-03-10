from __future__ import annotations

import time

from app.core.jobs import get_job_worker
from presentation.services.system_metrics.providers.base import MetricReading, SystemMetricsProvider

try:
    import psutil  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback for minimal runtime envs
    psutil = None  # type: ignore[assignment]


class RuntimeMetricsProvider(SystemMetricsProvider):
    name = "runtime"

    def __init__(self) -> None:
        process = None
        if psutil is not None:
            try:
                process = psutil.Process()
            except Exception:
                process = None

        self._process = process
        self._process_start = float(process.create_time()) if process is not None else time.time()
        self._cpu_initialized = False

    async def collect(self) -> list[MetricReading]:
        cpu_percent, memory_percent = self._read_utilization()

        worker = get_job_worker()
        active_workers = 1 if bool(getattr(worker, "_running", False)) else 0

        uptime_seconds = max(0, int(time.time() - self._process_start))

        return [
            MetricReading(
                key="cpu",
                title="CPU",
                value=cpu_percent,
                formatted_value=(f"{cpu_percent:.1f}%" if cpu_percent is not None else "n/a"),
                subtitle="Process CPU usage",
                unit="percent",
                status=_utilization_status(cpu_percent),
            ),
            MetricReading(
                key="ram",
                title="RAM",
                value=memory_percent,
                formatted_value=(f"{memory_percent:.1f}%" if memory_percent is not None else "n/a"),
                subtitle="System memory usage",
                unit="percent",
                status=_utilization_status(memory_percent),
            ),
            MetricReading(
                key="active_workers",
                title="Active Workers",
                value=active_workers,
                formatted_value=str(active_workers),
                subtitle="Background job worker state",
                unit="count",
                status="ok" if active_workers > 0 else "warning",
            ),
            MetricReading(
                key="uptime",
                title="Uptime",
                value=float(uptime_seconds),
                formatted_value=_format_uptime(uptime_seconds),
                subtitle="Current process uptime",
                unit="seconds",
                status="ok",
            ),
        ]

    def _read_utilization(self) -> tuple[float | None, float | None]:
        if self._process is None or psutil is None:
            return None, None

        try:
            if not self._cpu_initialized:
                self._process.cpu_percent(interval=None)
                self._cpu_initialized = True
            cpu_percent = max(0.0, float(self._process.cpu_percent(interval=None)))
        except Exception:
            cpu_percent = None

        try:
            memory_percent = max(0.0, float(psutil.virtual_memory().percent))
        except Exception:
            memory_percent = None

        return cpu_percent, memory_percent


def _utilization_status(percent: float | None) -> str:
    if percent is None:
        return "warning"
    if percent >= 90:
        return "critical"
    if percent >= 75:
        return "warning"
    return "ok"


def _format_uptime(total_seconds: int) -> str:
    days, rem = divmod(total_seconds, 86_400)
    hours, rem = divmod(rem, 3_600)
    minutes, seconds = divmod(rem, 60)

    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

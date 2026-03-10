from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MetricReading:
    key: str
    title: str
    value: float | int | None
    formatted_value: str
    subtitle: str
    unit: str = ""
    status: str = "normal"


class SystemMetricsProvider(Protocol):
    """Pluggable provider contract for system metric readings."""

    name: str

    async def collect(self) -> list[MetricReading]:
        ...

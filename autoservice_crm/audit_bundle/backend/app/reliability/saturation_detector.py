from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.reliability.saturation import SaturationReport, get_saturation_detector


@dataclass(frozen=True)
class SaturationSnapshot:
    checked_at: datetime
    status: str
    score: float
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at.isoformat(),
            "status": self.status,
            "score": self.score,
            "report": self.report,
        }


def classify_saturation(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.2:
        return "moderate"
    return "low"


async def collect_saturation_snapshot() -> SaturationSnapshot:
    report: SaturationReport = await get_saturation_detector().collect()
    score = float(report.saturation_score)
    return SaturationSnapshot(
        checked_at=datetime.now(UTC),
        status=classify_saturation(score),
        score=score,
        report=report.to_dict(),
    )

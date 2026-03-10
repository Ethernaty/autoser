from dataclasses import dataclass
from typing import Optional


# Статусы как константы — чтобы не гадать "in_progress" или "inProgress"
STATUS_ACCEPTED = "accepted"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"

STATUS_LABELS = {
    STATUS_ACCEPTED: "Принят",
    STATUS_IN_PROGRESS: "В работе",
    STATUS_COMPLETED: "Завершён",
}


@dataclass
class WorkOrder:
    client_id: int
    vehicle_id: int
    status: str = STATUS_ACCEPTED
    notes: str = ""
    total_amount: float = 0.0
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "WorkOrder":
        if row is None:
            return None
        return cls(
            id=row["id"],
            client_id=row["client_id"],
            vehicle_id=row["vehicle_id"],
            status=row["status"],
            notes=row["notes"] or "",
            total_amount=row["total_amount"] or 0.0,
            created_at=row["created_at"],
        )

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

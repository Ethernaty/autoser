from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkItem:
    work_order_id: int
    name: str
    price: float = 0.0
    employee_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "WorkItem":
        if row is None:
            return None
        return cls(
            id=row["id"],
            work_order_id=row["work_order_id"],
            name=row["name"],
            price=row["price"] or 0.0,
            employee_id=row["employee_id"],
            created_at=row["created_at"],
        )

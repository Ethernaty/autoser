from dataclasses import dataclass
from typing import Optional


@dataclass
class Employee:
    full_name: str
    commission_pct: int = 40
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Employee":
        if row is None:
            return None
        return cls(
            id=row["id"],
            full_name=row["full_name"],
            commission_pct=row["commission_pct"],
            created_at=row["created_at"],
        )

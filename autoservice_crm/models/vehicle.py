from dataclasses import dataclass
from typing import Optional


@dataclass
class Vehicle:
    client_id: int
    make: str
    model: str
    vin: str = ""
    license_plate: str = ""
    year: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Vehicle":
        if row is None:
            return None
        return cls(
            id=row["id"],
            client_id=row["client_id"],
            make=row["make"],
            model=row["model"],
            vin=row["vin"] if "vin" in row.keys() else "",
            license_plate=row["license_plate"] or "",
            year=row["year"],
            created_at=row["created_at"],
        )

    @property
    def display_name(self) -> str:
        plate = f" [{self.license_plate}]" if self.license_plate else ""
        return f"{self.make} {self.model}{plate}"

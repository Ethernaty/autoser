from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from models.vehicle import Vehicle
from repositories.client_repo import ClientRepository
from repositories.vehicle_repo import VehicleRepository
from services.errors import BusinessRuleError, NotFoundError
from services.validators import (
    normalize_optional_text,
    normalize_vin,
    require_non_empty,
    validate_id,
    validate_year,
)


@dataclass
class VehicleListRow:
    id: int
    make: str
    model: str
    vin: str
    license_plate: str
    year: Optional[int]
    owner_name: str


class VehicleService:
    def __init__(
        self,
        repo: VehicleRepository | None = None,
        client_repo: ClientRepository | None = None,
    ):
        self.repo = repo or VehicleRepository()
        self.client_repo = client_repo or ClientRepository()

    def list_vehicles(self, search: str = "") -> List[VehicleListRow]:
        rows = self.repo.get_all_with_owner((search or "").strip())
        return [
            VehicleListRow(
                id=row["id"],
                make=row["make"],
                model=row["model"],
                vin=row["vin"] or "",
                license_plate=row["license_plate"] or "",
                year=row["year"],
                owner_name=row["owner_name"] or "—",
            )
            for row in rows
        ]

    def get_vehicle(self, vehicle_id: int) -> Vehicle:
        vehicle = self.repo.get_by_id(validate_id(vehicle_id, "Автомобиль"))
        if not vehicle:
            raise NotFoundError("Автомобиль не найден.")
        return vehicle

    def list_by_client(self, client_id: int) -> List[Vehicle]:
        validate_id(client_id, "Клиент")
        return self.repo.get_by_client_id(client_id)

    def create_vehicle(
        self,
        *,
        client_id: int,
        make: str,
        model: str,
        vin: str = "",
        license_plate: str = "",
        year: Optional[int] = None,
    ) -> Vehicle:
        client = self.client_repo.get_by_id(validate_id(client_id, "Владелец"))
        if not client:
            raise BusinessRuleError("Нельзя создать автомобиль без существующего клиента.")

        vehicle = Vehicle(
            client_id=client_id,
            make=require_non_empty(make, "Марка"),
            model=require_non_empty(model, "Модель"),
            vin=normalize_vin(vin),
            license_plate=normalize_optional_text(license_plate, max_len=20).upper(),
            year=validate_year(year),
        )
        return self.repo.create(vehicle)

    def update_vehicle(
        self,
        vehicle_id: int,
        *,
        client_id: int,
        make: str,
        model: str,
        vin: str = "",
        license_plate: str = "",
        year: Optional[int] = None,
    ) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)
        client = self.client_repo.get_by_id(validate_id(client_id, "Владелец"))
        if not client:
            raise BusinessRuleError("Нельзя назначить несуществующего владельца.")

        vehicle.client_id = client_id
        vehicle.make = require_non_empty(make, "Марка")
        vehicle.model = require_non_empty(model, "Модель")
        vehicle.vin = normalize_vin(vin)
        vehicle.license_plate = normalize_optional_text(license_plate, max_len=20).upper()
        vehicle.year = validate_year(year)
        return self.repo.update(vehicle)

    def delete_vehicle(self, vehicle_id: int) -> None:
        self.get_vehicle(vehicle_id)
        self.repo.delete(vehicle_id)

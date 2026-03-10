from contextlib import closing
from typing import List, Optional

from database.connection import get_connection
from models.vehicle import Vehicle


class VehicleRepository:
    def get_all(self, search: str = "") -> List[Vehicle]:
        with closing(get_connection()) as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    """
                    SELECT * FROM vehicles
                    WHERE make LIKE ? OR model LIKE ? OR license_plate LIKE ? OR vin LIKE ?
                    ORDER BY make, model
                    """,
                    (like, like, like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM vehicles ORDER BY make, model"
                ).fetchall()
        return [Vehicle.from_row(r) for r in rows]

    def get_all_with_owner(self, search: str = ""):
        with closing(get_connection()) as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    """
                    SELECT
                        v.*,
                        c.full_name AS owner_name
                    FROM vehicles v
                    LEFT JOIN clients c ON c.id = v.client_id
                    WHERE v.make LIKE ?
                       OR v.model LIKE ?
                       OR v.license_plate LIKE ?
                       OR v.vin LIKE ?
                       OR c.full_name LIKE ?
                    ORDER BY v.make, v.model
                    """,
                    (like, like, like, like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        v.*,
                        c.full_name AS owner_name
                    FROM vehicles v
                    LEFT JOIN clients c ON c.id = v.client_id
                    ORDER BY v.make, v.model
                    """
                ).fetchall()
        return rows

    def get_by_client_id(self, client_id: int) -> List[Vehicle]:
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT * FROM vehicles WHERE client_id = ? ORDER BY make, model",
                (client_id,),
            ).fetchall()
        return [Vehicle.from_row(r) for r in rows]

    def get_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM vehicles WHERE id = ?",
                (vehicle_id,),
            ).fetchone()
        return Vehicle.from_row(row)

    def create(self, vehicle: Vehicle) -> Vehicle:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO vehicles (client_id, make, model, vin, license_plate, year)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    vehicle.client_id,
                    vehicle.make,
                    vehicle.model,
                    vehicle.vin,
                    vehicle.license_plate,
                    vehicle.year,
                ),
            )
            vehicle.id = cursor.lastrowid
            conn.commit()
        return vehicle

    def update(self, vehicle: Vehicle) -> Vehicle:
        with closing(get_connection()) as conn:
            conn.execute(
                """
                UPDATE vehicles
                SET client_id=?, make=?, model=?, vin=?, license_plate=?, year=?
                WHERE id=?
                """,
                (
                    vehicle.client_id,
                    vehicle.make,
                    vehicle.model,
                    vehicle.vin,
                    vehicle.license_plate,
                    vehicle.year,
                    vehicle.id,
                ),
            )
            conn.commit()
        return vehicle

    def delete(self, vehicle_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
            conn.commit()

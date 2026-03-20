from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import guard_against_sqli, sanitize_text
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.repositories.client_repository import ClientRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.base_service import BaseService


class VehicleService(BaseService):
    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
        )

    async def create_vehicle(
        self,
        *,
        client_id: UUID,
        plate_number: str,
        make_model: str,
        year: int | None = None,
        vin: str | None = None,
        comment: str | None = None,
    ) -> Vehicle:
        normalized_plate = self._normalize_plate(plate_number)
        normalized_model = self._normalize_required(make_model, field="make_model", max_length=120)
        normalized_vin = self._normalize_optional(vin, max_length=64)
        normalized_comment = self._normalize_optional(comment, max_length=2000)

        def write_op(db: Session) -> Vehicle:
            client_repo = ClientRepository(db=db, tenant_id=self.tenant_id)
            if client_repo.get_by_id(client_id) is None:
                raise AppError(status_code=404, code="client_not_found", message="Client not found")
            repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            return repo.create(
                client_id=client_id,
                plate_number=normalized_plate,
                make_model=normalized_model,
                year=year,
                vin=normalized_vin,
                comment=normalized_comment,
            )

        return await self.execute_write(write_op, idempotent=False)

    async def get_vehicle(self, *, vehicle_id: UUID) -> Vehicle:
        def read_op(db: Session) -> Vehicle:
            repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            vehicle = repo.get_by_id(vehicle_id)
            if vehicle is None:
                raise AppError(status_code=404, code="vehicle_not_found", message="Vehicle not found")
            return vehicle

        return await self.execute_read(read_op)

    async def list_vehicles(
        self,
        *,
        q: str | None,
        client_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Vehicle], int]:
        if limit <= 0 or offset < 0 or limit > 100:
            raise AppError(status_code=400, code="invalid_pagination", message="Invalid pagination")
        normalized_query = guard_against_sqli(q.strip())[:100] if q else None

        def read_op(db: Session) -> tuple[list[Vehicle], int]:
            repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            items = repo.paginate(limit=limit, offset=offset, query=normalized_query, client_id=client_id)
            total = repo.count(query=normalized_query, client_id=client_id)
            return items, total

        return await self.execute_read(read_op)

    async def list_by_client(self, *, client_id: UUID) -> list[Vehicle]:
        def read_op(db: Session) -> list[Vehicle]:
            repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_by_client(client_id=client_id)

        return await self.execute_read(read_op)

    async def update_vehicle(
        self,
        *,
        vehicle_id: UUID,
        plate_number: str | None = None,
        make_model: str | None = None,
        year: int | None = None,
        vin: str | None = None,
        comment: str | None = None,
        archived: bool | None = None,
    ) -> Vehicle:
        updates: dict[str, object] = {}
        if plate_number is not None:
            updates["plate_number"] = self._normalize_plate(plate_number)
        if make_model is not None:
            updates["make_model"] = self._normalize_required(make_model, field="make_model", max_length=120)
        if year is not None:
            updates["year"] = year
        if vin is not None:
            updates["vin"] = self._normalize_optional(vin, max_length=64)
        if comment is not None:
            updates["comment"] = self._normalize_optional(comment, max_length=2000)
        if archived is not None:
            updates["archived_at"] = datetime.now(UTC) if archived else None

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> Vehicle:
            repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            vehicle = repo.update(vehicle_id, **updates)
            if vehicle is None:
                raise AppError(status_code=404, code="vehicle_not_found", message="Vehicle not found")
            return vehicle

        return await self.execute_write(write_op, idempotent=False)

    async def list_work_order_history(
        self,
        *,
        vehicle_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Order]:
        if limit <= 0 or offset < 0 or limit > 100:
            raise AppError(status_code=400, code="invalid_pagination", message="Invalid pagination")

        def read_op(db: Session) -> list[Order]:
            vehicle_repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
            if vehicle_repo.get_by_id(vehicle_id) is None:
                raise AppError(status_code=404, code="vehicle_not_found", message="Vehicle not found")

            order_repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            orders = order_repo.list(Order.vehicle_id == vehicle_id)
            orders.sort(key=lambda item: item.created_at, reverse=True)
            return orders[offset : offset + limit]

        return await self.execute_read(read_op)

    @staticmethod
    def _normalize_required(value: str, *, field: str, max_length: int) -> str:
        normalized = sanitize_text(value, max_length=max_length)
        if not normalized:
            raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}")
        return normalized

    @staticmethod
    def _normalize_optional(value: str | None, *, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = sanitize_text(value, max_length=max_length)
        return normalized if normalized else None

    @staticmethod
    def _normalize_plate(value: str) -> str:
        normalized = sanitize_text(value, max_length=20)
        if not normalized:
            raise AppError(status_code=400, code="invalid_plate_number", message="Invalid plate number")
        return normalized.upper().replace(" ", "")

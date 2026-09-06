from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle
from app.models.order import Order, OrderStatus
from app.repositories.base import BaseRepositoryTenantScoped


class VehicleRepository(BaseRepositoryTenantScoped[Vehicle]):
    """Tenant-scoped data access for vehicles."""

    ALLOWED_UPDATE_FIELDS = {"plate_number", "make_model", "year", "vin", "comment", "archived_at"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Vehicle, tenant_id=tenant_id)

    def get_by_id(self, entity_id: UUID) -> Vehicle | None:
        stmt = self.scoped_select(Vehicle.id == entity_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_ids(self, ids: list[UUID], *, include_archived: bool = True) -> list[Vehicle]:
        if not ids:
            return []
        criteria: list[object] = [Vehicle.id.in_(ids)]
        if not include_archived:
            criteria.append(Vehicle.archived_at.is_(None))
        stmt = self.scoped_select(*criteria)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_client(self, *, client_id: UUID, include_archived: bool = False) -> list[Vehicle]:
        criteria: list[object] = [Vehicle.client_id == client_id]
        if not include_archived:
            criteria.append(Vehicle.archived_at.is_(None))
        stmt = self.scoped_select(*criteria).order_by(Vehicle.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def paginate(self, *, limit: int, offset: int, query: str | None = None, client_id: UUID | None = None) -> list[Vehicle]:
        criteria: list[object] = [Vehicle.archived_at.is_(None)]
        if client_id is not None:
            criteria.append(Vehicle.client_id == client_id)
        if query:
            pattern = f"%{query}%"
            criteria.append(
                or_(
                    Vehicle.plate_number.ilike(pattern),
                    Vehicle.make_model.ilike(pattern),
                    Vehicle.vin.ilike(pattern),
                )
            )

        stmt: Select[tuple[Vehicle]] = self.scoped_select(*criteria).order_by(Vehicle.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, *, query: str | None = None, client_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Vehicle).where(
            Vehicle.tenant_id == self.tenant_id,
            Vehicle.archived_at.is_(None),
        )
        if client_id is not None:
            stmt = stmt.where(Vehicle.client_id == client_id)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Vehicle.plate_number.ilike(pattern),
                    Vehicle.make_model.ilike(pattern),
                    Vehicle.vin.ilike(pattern),
                )
            )
        return int(self.db.execute(stmt).scalar_one())

    def summary(self, *, query: str | None = None, client_id: UUID | None = None) -> dict[str, int]:
        criteria: list[object] = [
            Vehicle.tenant_id == self.tenant_id,
            Vehicle.archived_at.is_(None),
        ]
        if client_id is not None:
            criteria.append(Vehicle.client_id == client_id)
        if query:
            pattern = f"%{query}%"
            criteria.append(
                or_(
                    Vehicle.plate_number.ilike(pattern),
                    Vehicle.make_model.ilike(pattern),
                    Vehicle.vin.ilike(pattern),
                )
            )

        filtered = select(Vehicle.id, Vehicle.created_at).where(*criteria).subquery()
        stmt = (
            select(
                func.count(func.distinct(case((Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS]), filtered.c.id)))).label(
                    "with_active_orders"
                ),
                func.count(func.distinct(case((Order.id.is_(None), filtered.c.id)))).label("without_orders"),
                func.count(
                    func.distinct(case((filtered.c.created_at >= datetime.now(UTC) - timedelta(days=14), filtered.c.id)))
                ).label("recent_added"),
            )
            .select_from(filtered)
            .outerjoin(Order, (Order.tenant_id == self.tenant_id) & (Order.vehicle_id == filtered.c.id))
        )
        row = self.db.execute(stmt).one()
        return {
            "with_active_orders": int(row.with_active_orders or 0),
            "without_orders": int(row.without_orders or 0),
            "recent_added": int(row.recent_added or 0),
        }

    def count_by_client_ids(self, *, client_ids: list[UUID], include_archived: bool = False) -> dict[UUID, int]:
        if not client_ids:
            return {}

        stmt = (
            select(Vehicle.client_id, func.count(Vehicle.id))
            .where(
                Vehicle.tenant_id == self.tenant_id,
                Vehicle.client_id.in_(client_ids),
            )
            .group_by(Vehicle.client_id)
        )
        if not include_archived:
            stmt = stmt.where(Vehicle.archived_at.is_(None))

        rows = self.db.execute(stmt).all()
        result: dict[UUID, int] = {}
        for client_id, count in rows:
            result[client_id] = int(count or 0)
        return result

    def update(self, vehicle_id: UUID, **updates: object) -> Vehicle | None:
        vehicle = self.get_by_id(vehicle_id)
        if vehicle is None:
            return None
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(vehicle, field, value)
        self.db.flush()
        self.db.refresh(vehicle)
        return vehicle

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import Plan


class PlanRepository:
    """Data-access layer for commercial plans."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: UUID) -> Plan | None:
        stmt = select(Plan).where(Plan.id == plan_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, name: str) -> Plan | None:
        stmt = select(Plan).where(Plan.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_active(self) -> list[Plan]:
        stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price.asc(), Plan.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        name: str,
        price: Decimal,
        limits_json: dict[str, Any] | None = None,
        features_json: dict[str, Any] | None = None,
        is_active: bool = True,
        description: str | None = None,
    ) -> Plan:
        plan = Plan(
            name=name,
            price=price,
            limits_json=limits_json or {},
            features_json=features_json or {},
            is_active=is_active,
            description=description,
        )
        self.db.add(plan)
        self.db.flush()
        return plan

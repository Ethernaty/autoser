from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.work_order_assignee import WorkOrderAssignee
from app.repositories.base import BaseRepositoryTenantScoped


class OrderRepository(BaseRepositoryTenantScoped[Order]):
    """Tenant-scoped data access for work orders."""

    ALLOWED_UPDATE_FIELDS = {"description", "total_amount", "status", "vehicle_id", "assigned_user_id"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Order, tenant_id=tenant_id)

    def paginate(
        self,
        *,
        limit: int,
        offset: int,
        status_scope: str = "all",
        assignee_scope: str = "all",
    ) -> list[Order]:
        stmt = (
            self.scoped_select(*self._build_scope_criteria(status_scope=status_scope, assignee_scope=assignee_scope))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
        status_scope: str = "all",
        assignee_scope: str = "all",
    ) -> list[Order]:
        pattern = f"%{query}%"
        stmt = (
            self.scoped_select(
                *self._build_scope_criteria(status_scope=status_scope, assignee_scope=assignee_scope),
                or_(
                    cast(Order.order_number, String).ilike(pattern),
                    Order.description.ilike(pattern),
                    cast(Order.status, String).ilike(pattern),
                )
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def update(self, order_id: UUID, **updates: object) -> Order | None:
        order = self.get_by_id(order_id)
        if order is None:
            return None
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(order, field, value)
        self.db.flush()
        self.db.refresh(order)
        return order

    def count(self, *, query: str | None = None, status_scope: str = "all", assignee_scope: str = "all") -> int:
        stmt = select(func.count()).select_from(Order).where(Order.tenant_id == self.tenant_id)
        for criterion in self._build_scope_criteria(status_scope=status_scope, assignee_scope=assignee_scope):
            stmt = stmt.where(criterion)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    cast(Order.order_number, String).ilike(pattern),
                    Order.description.ilike(pattern),
                    cast(Order.status, String).ilike(pattern),
                )
            )
        return int(self.db.execute(stmt).scalar_one())

    def get_next_order_number(self) -> int:
        stmt = select(func.coalesce(func.max(Order.order_number), 0) + 1).where(Order.tenant_id == self.tenant_id)
        return int(self.db.execute(stmt).scalar_one())

    def exists_client(self, *, client_id: UUID) -> bool:
        stmt = select(func.count()).select_from(Order).where(
            Order.tenant_id == self.tenant_id,
            Order.client_id == client_id,
        )
        return int(self.db.execute(stmt).scalar_one()) > 0

    def stats_by_client_ids(self, *, client_ids: list[UUID]) -> dict[UUID, tuple[int, int, datetime | None]]:
        if not client_ids:
            return {}

        active_case = case(
            (Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED_UNPAID]), 1),
            else_=0,
        )
        rows = self.db.execute(
            select(
                Order.client_id,
                func.count(Order.id),
                func.coalesce(func.sum(active_case), 0),
                func.max(Order.updated_at),
            )
            .where(
                Order.tenant_id == self.tenant_id,
                Order.client_id.in_(client_ids),
            )
            .group_by(Order.client_id)
        ).all()

        result: dict[UUID, tuple[int, int, datetime | None]] = {}
        for client_id, total_count, active_count, last_activity_at in rows:
            result[client_id] = (int(total_count or 0), int(active_count or 0), last_activity_at)
        return result

    def stats_by_vehicle_ids(self, *, vehicle_ids: list[UUID]) -> dict[UUID, tuple[int, int, datetime | None]]:
        if not vehicle_ids:
            return {}

        active_case = case(
            (Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED_UNPAID]), 1),
            else_=0,
        )
        rows = self.db.execute(
            select(
                Order.vehicle_id,
                func.count(Order.id),
                func.coalesce(func.sum(active_case), 0),
                func.max(Order.updated_at),
            )
            .where(
                Order.tenant_id == self.tenant_id,
                Order.vehicle_id.is_not(None),
                Order.vehicle_id.in_(vehicle_ids),
            )
            .group_by(Order.vehicle_id)
        ).all()

        result: dict[UUID, tuple[int, int, datetime | None]] = {}
        for vehicle_id, total_count, active_count, last_activity_at in rows:
            if vehicle_id is None:
                continue
            result[vehicle_id] = (int(total_count or 0), int(active_count or 0), last_activity_at)
        return result

    @staticmethod
    def normalize_total_amount(value: float | Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"))

    def _build_scope_criteria(self, *, status_scope: str, assignee_scope: str) -> list[object]:
        criteria: list[object] = []
        normalized_status_scope = self._normalize_status_scope(status_scope)
        normalized_assignee_scope = self._normalize_assignee_scope(assignee_scope)

        status_criteria = self._status_scope_criteria(normalized_status_scope)
        if status_criteria is not None:
            criteria.append(status_criteria)

        assignee_criteria = self._assignee_scope_criteria(normalized_assignee_scope)
        if assignee_criteria is not None:
            criteria.append(assignee_criteria)

        return criteria

    @staticmethod
    def _normalize_status_scope(raw_scope: str | None) -> str:
        candidate = str(raw_scope or "all").strip().lower()
        allowed = {
            "all",
            "active",
            "completed",
            "cancelled",
            "completed_unpaid",
            "new",
            "in_progress",
            "completed_paid",
        }
        if candidate in allowed:
            return candidate
        return "all"

    @staticmethod
    def _normalize_assignee_scope(raw_scope: str | None) -> str:
        candidate = str(raw_scope or "all").strip().lower()
        if candidate in {"all", "unassigned"}:
            return candidate
        try:
            return str(UUID(str(raw_scope)))
        except Exception:
            return "all"

    @staticmethod
    def _status_scope_criteria(scope: str) -> object | None:
        if scope == "all":
            return None
        if scope == "active":
            return Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS])
        if scope == "completed":
            return Order.status.in_([OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID])
        if scope == "cancelled":
            return Order.status == OrderStatus.CANCELLED
        if scope == "completed_unpaid":
            return Order.status == OrderStatus.COMPLETED_UNPAID
        if scope == "new":
            return Order.status == OrderStatus.NEW
        if scope == "in_progress":
            return Order.status == OrderStatus.IN_PROGRESS
        if scope == "completed_paid":
            return Order.status == OrderStatus.COMPLETED_PAID
        return None

    def _assignee_scope_criteria(self, scope: str) -> object | None:
        if scope == "all":
            return None

        if scope == "unassigned":
            return (
                (Order.assigned_user_id.is_(None))
                & (
                    ~exists(
                        select(1).where(
                            WorkOrderAssignee.tenant_id == self.tenant_id,
                            WorkOrderAssignee.order_id == Order.id,
                        )
                    )
                )
            )

        try:
            assignee_id = UUID(scope)
        except Exception:
            return None

        return or_(
            Order.assigned_user_id == assignee_id,
            exists(
                select(1).where(
                    WorkOrderAssignee.tenant_id == self.tenant_id,
                    WorkOrderAssignee.order_id == Order.id,
                    WorkOrderAssignee.user_id == assignee_id,
                )
            ),
        )

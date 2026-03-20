from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import guard_against_sqli, sanitize_text
from app.models.audit_log import AuditLog
from app.models.membership import Membership, MembershipRole
from app.models.order import Order, OrderStatus
from app.models.order_line import OrderLine, OrderLineType
from app.models.payment import Payment, PaymentMethod
from app.repositories.client_repository import ClientRepository
from app.repositories.order_line_repository import OrderLineRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.audit_decorator import audit
from app.services.audit_log_service import AuditLogService
from app.services.base_service import BaseService


_MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class WorkOrderFinancials:
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal


class WorkOrderService(BaseService):
    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self.max_limit = get_settings().max_limit
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
        )
        self.audit_service = AuditLogService(tenant_id=tenant_id, session_factory=self._session_factory)

    async def get_work_order(self, *, work_order_id: UUID) -> Order:
        def read_op(db: Session) -> Order:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            order = repo.get_by_id(work_order_id)
            if order is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            return order

        return await self.execute_read(read_op)

    async def list_work_orders(
        self,
        *,
        q: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Order], int]:
        self._validate_pagination(limit=limit, offset=offset)
        normalized_query = guard_against_sqli(q.strip())[:100] if q else None

        def read_op(db: Session) -> tuple[list[Order], int]:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            if normalized_query:
                items = repo.search(query=normalized_query, limit=limit, offset=offset)
                total = repo.count(query=normalized_query)
            else:
                items = repo.paginate(limit=limit, offset=offset)
                total = repo.count(query=None)
            return items, total

        return await self.execute_read(read_op)

    @audit(action="create", entity="work_order")
    async def create_work_order(
        self,
        *,
        client_id: UUID,
        vehicle_id: UUID,
        description: str,
        total_amount: Decimal,
        status: OrderStatus = OrderStatus.NEW,
        assigned_user_id: UUID | None = None,
    ) -> Order:
        normalized_description = self._normalize_description(description)
        normalized_total = self._normalize_money(total_amount, field="total_amount")
        normalized_status = self._normalize_status(status)

        def write_op(db: Session) -> Order:
            self._assert_client_exists(db=db, client_id=client_id)
            self._assert_vehicle_link(db=db, client_id=client_id, vehicle_id=vehicle_id)
            self._assert_assignee_valid(db=db, assigned_user_id=assigned_user_id)

            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            return repo.create(
                client_id=client_id,
                vehicle_id=vehicle_id,
                assigned_user_id=assigned_user_id,
                description=normalized_description,
                total_amount=normalized_total,
                status=normalized_status,
            )

        return await self.execute_write(write_op, idempotent=False)

    @audit(action="update", entity="work_order")
    async def update_work_order(
        self,
        *,
        work_order_id: UUID,
        description: str | None = None,
        total_amount: Decimal | None = None,
        status: OrderStatus | None = None,
        vehicle_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> Order:
        updates: dict[str, object] = {}
        if description is not None:
            updates["description"] = self._normalize_description(description)
        if total_amount is not None:
            updates["total_amount"] = self._normalize_money(total_amount, field="total_amount")
        if status is not None:
            updates["status"] = self._normalize_status(status)
        if vehicle_id is not None:
            updates["vehicle_id"] = vehicle_id
        if assigned_user_id is not None:
            updates["assigned_user_id"] = assigned_user_id

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> Order:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")

            if "status" in updates and isinstance(updates["status"], OrderStatus):
                self._assert_status_transition(current=current.status, target=updates["status"])  # type: ignore[arg-type]
            if "vehicle_id" in updates:
                self._assert_vehicle_link(db=db, client_id=current.client_id, vehicle_id=updates["vehicle_id"])  # type: ignore[arg-type]
            if "assigned_user_id" in updates:
                self._assert_assignee_valid(db=db, assigned_user_id=updates["assigned_user_id"])  # type: ignore[arg-type]

            updated = repo.update(work_order_id, **updates)
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            return updated

        return await self.execute_write(write_op, idempotent=False)

    async def set_status(self, *, work_order_id: UUID, status: OrderStatus) -> Order:
        return await self.update_work_order(work_order_id=work_order_id, status=status)

    @audit(action="close", entity="work_order")
    async def close_work_order(self, *, work_order_id: UUID) -> Order:
        return await self.update_work_order(work_order_id=work_order_id, status=OrderStatus.COMPLETED)

    @audit(action="delete", entity="work_order")
    async def delete_work_order(self, *, work_order_id: UUID) -> None:
        def write_op(db: Session) -> None:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            if not repo.delete_by_id(work_order_id):
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")

        await self.execute_write(write_op, idempotent=False)

    @audit(action="update", entity="work_order")
    async def assign_employee(self, *, work_order_id: UUID, assigned_user_id: UUID | None) -> Order:
        def write_op(db: Session) -> Order:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            self._assert_assignee_valid(db=db, assigned_user_id=assigned_user_id)
            updated = repo.update(work_order_id, assigned_user_id=assigned_user_id)
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            return updated

        return await self.execute_write(write_op, idempotent=False)

    @audit(action="update", entity="work_order")
    async def attach_vehicle(self, *, work_order_id: UUID, vehicle_id: UUID) -> Order:
        def write_op(db: Session) -> Order:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            self._assert_vehicle_link(db=db, client_id=current.client_id, vehicle_id=vehicle_id)
            updated = repo.update(work_order_id, vehicle_id=vehicle_id)
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            return updated

        return await self.execute_write(write_op, idempotent=False)

    async def list_order_lines(self, *, work_order_id: UUID) -> list[OrderLine]:
        def read_op(db: Session) -> list[OrderLine]:
            self._assert_order_exists(db=db, work_order_id=work_order_id)
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_for_order(order_id=work_order_id)

        return await self.execute_read(read_op)

    @audit(action="create", entity="work_order_line")
    async def add_order_line(
        self,
        *,
        work_order_id: UUID,
        line_type: OrderLineType | str,
        name: str,
        quantity: Decimal,
        unit_price: Decimal,
        position: int | None = None,
        comment: str | None = None,
    ) -> OrderLine:
        normalized_line_type = self._normalize_line_type(line_type)
        normalized_name = self._normalize_line_name(name)
        normalized_quantity = self._normalize_line_quantity(quantity)
        normalized_unit_price = self._normalize_money(unit_price, field="unit_price")
        normalized_comment = self._normalize_optional_comment(comment)
        line_total = (normalized_quantity * normalized_unit_price).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)

        def write_op(db: Session) -> OrderLine:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            self._assert_order_lines_editable(order.status)

            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            line = repo.create(
                order_id=work_order_id,
                line_type=normalized_line_type,
                name=normalized_name,
                quantity=normalized_quantity,
                unit_price=normalized_unit_price,
                line_total=line_total,
                position=max(0, int(position or 0)),
                comment=normalized_comment,
            )
            self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)
            return line

        return await self.execute_write(write_op, idempotent=False)

    @audit(action="update", entity="work_order_line")
    async def update_order_line(
        self,
        *,
        work_order_id: UUID,
        line_id: UUID,
        line_type: OrderLineType | str | None = None,
        name: str | None = None,
        quantity: Decimal | None = None,
        unit_price: Decimal | None = None,
        position: int | None = None,
        comment: str | None = None,
    ) -> OrderLine:
        def write_op(db: Session) -> OrderLine:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            self._assert_order_lines_editable(order.status)
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            line = repo.get_by_id(line_id)
            if line is None or line.order_id != work_order_id:
                raise AppError(status_code=404, code="order_line_not_found", message="Order line not found")

            updates: dict[str, object] = {}
            if line_type is not None:
                updates["line_type"] = self._normalize_line_type(line_type)
            if name is not None:
                updates["name"] = self._normalize_line_name(name)
            if quantity is not None:
                updates["quantity"] = self._normalize_line_quantity(quantity)
            if unit_price is not None:
                updates["unit_price"] = self._normalize_money(unit_price, field="unit_price")
            if position is not None:
                updates["position"] = max(0, int(position))
            if comment is not None:
                updates["comment"] = self._normalize_optional_comment(comment)

            new_quantity = updates.get("quantity", line.quantity)
            new_unit_price = updates.get("unit_price", line.unit_price)
            updates["line_total"] = (Decimal(new_quantity) * Decimal(new_unit_price)).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
            updated = repo.update(line_id, **updates)
            if updated is None:
                raise AppError(status_code=404, code="order_line_not_found", message="Order line not found")

            self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)
            return updated

        return await self.execute_write(write_op, idempotent=False)

    @audit(action="delete", entity="work_order_line")
    async def remove_order_line(self, *, work_order_id: UUID, line_id: UUID) -> None:
        def write_op(db: Session) -> None:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            self._assert_order_lines_editable(order.status)
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            line = repo.get_by_id(line_id)
            if line is None or line.order_id != work_order_id:
                raise AppError(status_code=404, code="order_line_not_found", message="Order line not found")
            db.delete(line)
            db.flush()
            self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)

        await self.execute_write(write_op, idempotent=False)

    @audit(action="create", entity="payment")
    async def create_payment(
        self,
        *,
        work_order_id: UUID,
        amount: Decimal,
        method: PaymentMethod | str = PaymentMethod.CASH,
        paid_at: datetime | None = None,
        comment: str | None = None,
        external_ref: str | None = None,
    ) -> Payment:
        if self.actor_user_id is None:
            raise AppError(status_code=401, code="actor_required", message="Authenticated actor is required")

        normalized_amount = self._normalize_money(amount, field="amount")
        normalized_method = self._normalize_payment_method(method)
        normalized_paid_at = paid_at.astimezone(UTC) if paid_at is not None else datetime.now(UTC)
        normalized_comment = self._normalize_optional_comment(comment)
        normalized_external_ref = self._normalize_optional_string(external_ref, max_length=120)

        def write_op(db: Session) -> Payment:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            financials = self._financials_in_tx(db=db, order=order)
            if normalized_amount > financials.remaining_amount:
                raise AppError(
                    status_code=400,
                    code="payment_exceeds_remaining",
                    message="Payment exceeds remaining amount",
                    details={
                        "remaining_amount": str(financials.remaining_amount),
                        "requested_amount": str(normalized_amount),
                    },
                )

            repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
            return repo.create(
                order_id=work_order_id,
                created_by_user_id=self.actor_user_id,
                amount=normalized_amount,
                method=normalized_method,
                paid_at=normalized_paid_at,
                comment=normalized_comment,
                external_ref=normalized_external_ref,
            )

        return await self.execute_write(write_op, idempotent=False)

    async def list_payments(self, *, work_order_id: UUID) -> list[Payment]:
        def read_op(db: Session) -> list[Payment]:
            self._assert_order_exists(db=db, work_order_id=work_order_id)
            repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_for_order(order_id=work_order_id)

        return await self.execute_read(read_op)

    async def get_financials(self, *, work_order_id: UUID) -> WorkOrderFinancials:
        def read_op(db: Session) -> WorkOrderFinancials:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            return self._financials_in_tx(db=db, order=order)

        return await self.execute_read(read_op)

    async def get_financials_map(self, *, work_order_ids: list[UUID]) -> dict[UUID, WorkOrderFinancials]:
        if not work_order_ids:
            return {}

        def read_op(db: Session) -> dict[UUID, WorkOrderFinancials]:
            rows = db.execute(
                select(Payment.order_id, func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.tenant_id == self.tenant_id,
                    Payment.order_id.in_(work_order_ids),
                    Payment.voided_at.is_(None),
                )
                .group_by(Payment.order_id)
            ).all()
            paid_map = {order_id: Decimal(total or 0).quantize(_MONEY_QUANT) for order_id, total in rows}

            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            result: dict[UUID, WorkOrderFinancials] = {}
            for work_order_id in work_order_ids:
                order = repo.get_by_id(work_order_id)
                if order is None:
                    continue
                paid = paid_map.get(work_order_id, Decimal("0.00"))
                total = Decimal(order.total_amount).quantize(_MONEY_QUANT)
                remaining = max(total - paid, Decimal("0.00")).quantize(_MONEY_QUANT)
                result[work_order_id] = WorkOrderFinancials(total_amount=total, paid_amount=paid, remaining_amount=remaining)
            return result

        return await self.execute_read(read_op)

    async def get_dashboard_summary(self, *, recent_limit: int = 10) -> dict[str, Any]:
        safe_limit = max(1, min(50, recent_limit))

        def read_op(db: Session) -> dict[str, Any]:
            open_count = int(
                db.execute(
                    select(func.count()).select_from(Order).where(
                        Order.tenant_id == self.tenant_id,
                        Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS]),
                    )
                ).scalar_one()
            )
            closed_count = int(
                db.execute(
                    select(func.count()).select_from(Order).where(
                        Order.tenant_id == self.tenant_id,
                        Order.status.in_([OrderStatus.COMPLETED, OrderStatus.CANCELED]),
                    )
                ).scalar_one()
            )
            revenue = Decimal(
                db.execute(
                    select(func.coalesce(func.sum(Payment.amount), 0)).where(
                        Payment.tenant_id == self.tenant_id,
                        Payment.voided_at.is_(None),
                    )
                ).scalar_one()
                or 0
            ).quantize(_MONEY_QUANT)

            recent_rows = db.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == self.tenant_id)
                .order_by(AuditLog.created_at.desc())
                .limit(safe_limit)
            ).scalars().all()

            return {
                "open_work_orders_count": open_count,
                "closed_work_orders_count": closed_count,
                "revenue_total": revenue,
                "recent_activity": [
                    {
                        "id": row.id,
                        "entity": row.entity,
                        "entity_id": row.entity_id,
                        "action": row.action,
                        "user_id": row.user_id,
                        "created_at": row.created_at,
                    }
                    for row in recent_rows
                ],
            }

        return await self.execute_read(read_op)

    def _assert_order_exists(self, *, db: Session, work_order_id: UUID) -> Order:
        repo = OrderRepository(db=db, tenant_id=self.tenant_id)
        order = repo.get_by_id(work_order_id)
        if order is None:
            raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
        return order

    def _assert_client_exists(self, *, db: Session, client_id: UUID) -> None:
        repo = ClientRepository(db=db, tenant_id=self.tenant_id)
        if repo.get_by_id(client_id) is None:
            raise AppError(status_code=404, code="client_not_found", message="Client not found")

    def _assert_vehicle_link(self, *, db: Session, client_id: UUID, vehicle_id: UUID | None) -> None:
        if vehicle_id is None:
            raise AppError(status_code=400, code="vehicle_required", message="Vehicle is required")
        repo = VehicleRepository(db=db, tenant_id=self.tenant_id)
        vehicle = repo.get_by_id(vehicle_id)
        if vehicle is None or vehicle.archived_at is not None:
            raise AppError(status_code=404, code="vehicle_not_found", message="Vehicle not found")
        if vehicle.client_id != client_id:
            raise AppError(
                status_code=400,
                code="vehicle_client_mismatch",
                message="Vehicle does not belong to selected client",
            )

    def _assert_assignee_valid(self, *, db: Session, assigned_user_id: UUID | None) -> None:
        if assigned_user_id is None:
            return
        membership = db.execute(
            select(Membership).where(
                Membership.tenant_id == self.tenant_id,
                Membership.user_id == assigned_user_id,
                Membership.role.in_(
                    [MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER, MembershipRole.EMPLOYEE]
                ),
            )
        ).scalar_one_or_none()
        if membership is None:
            raise AppError(status_code=404, code="employee_not_found", message="Employee not found in workspace")

    def _assert_status_transition(self, *, current: OrderStatus, target: OrderStatus) -> None:
        if current == target:
            return
        allowed: dict[OrderStatus, set[OrderStatus]] = {
            OrderStatus.NEW: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELED},
            OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELED},
            OrderStatus.COMPLETED: set(),
            OrderStatus.CANCELED: set(),
        }
        if target not in allowed.get(current, set()):
            raise AppError(
                status_code=400,
                code="invalid_status_transition",
                message="Invalid work-order status transition",
                details={"from": current.value, "to": target.value},
            )

    def _assert_order_lines_editable(self, status: OrderStatus) -> None:
        if status in {OrderStatus.COMPLETED, OrderStatus.CANCELED}:
            raise AppError(
                status_code=400,
                code="work_order_closed",
                message="Cannot modify lines for closed work order",
            )

    def _recalculate_total_in_tx(self, *, db: Session, work_order_id: UUID) -> None:
        line_repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
        lines = line_repo.list_for_order(order_id=work_order_id)
        total = sum((Decimal(line.line_total) for line in lines), Decimal("0.00")).quantize(_MONEY_QUANT)
        order_repo = OrderRepository(db=db, tenant_id=self.tenant_id)
        order_repo.update(work_order_id, total_amount=total)

    def _financials_in_tx(self, *, db: Session, order: Order) -> WorkOrderFinancials:
        pay_repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
        paid = pay_repo.sum_paid_for_order(order_id=order.id)
        total = Decimal(order.total_amount).quantize(_MONEY_QUANT)
        remaining = max(total - paid, Decimal("0.00")).quantize(_MONEY_QUANT)
        return WorkOrderFinancials(total_amount=total, paid_amount=paid, remaining_amount=remaining)

    def _validate_pagination(self, *, limit: int, offset: int) -> None:
        if limit <= 0 or limit > self.max_limit or offset < 0:
            raise AppError(
                status_code=400,
                code="invalid_pagination",
                message=f"Pagination must satisfy 0 < limit <= {self.max_limit} and offset >= 0",
            )

    @staticmethod
    def _normalize_description(value: str) -> str:
        normalized = sanitize_text(value, max_length=5000)
        if not normalized:
            raise AppError(status_code=400, code="invalid_description", message="Description is required")
        return normalized

    @staticmethod
    def _normalize_optional_comment(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = sanitize_text(value, max_length=2000)
        return normalized if normalized else None

    @staticmethod
    def _normalize_optional_string(value: str | None, *, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = sanitize_text(value, max_length=max_length)
        return normalized if normalized else None

    @staticmethod
    def _normalize_money(value: Decimal, *, field: str) -> Decimal:
        try:
            normalized = Decimal(value).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}") from exc
        if normalized <= 0:
            raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}")
        return normalized

    @staticmethod
    def _normalize_status(value: OrderStatus | str) -> OrderStatus:
        if isinstance(value, OrderStatus):
            return value
        try:
            return OrderStatus(str(value))
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_status", message="Invalid status") from exc

    @staticmethod
    def _normalize_line_type(value: OrderLineType | str) -> OrderLineType:
        if isinstance(value, OrderLineType):
            return value
        try:
            return OrderLineType(str(value).strip().lower())
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_line_type", message="Invalid line_type") from exc

    @staticmethod
    def _normalize_line_name(value: str) -> str:
        normalized = sanitize_text(value, max_length=200)
        if not normalized:
            raise AppError(status_code=400, code="invalid_line_name", message="Line name is required")
        return normalized

    @staticmethod
    def _normalize_line_quantity(value: Decimal) -> Decimal:
        try:
            normalized = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AppError(status_code=400, code="invalid_quantity", message="Invalid quantity") from exc
        if normalized <= 0:
            raise AppError(status_code=400, code="invalid_quantity", message="Invalid quantity")
        return normalized

    @staticmethod
    def _normalize_payment_method(value: PaymentMethod | str) -> PaymentMethod:
        if isinstance(value, PaymentMethod):
            return value
        try:
            return PaymentMethod(str(value).strip().lower())
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_payment_method", message="Invalid payment method") from exc

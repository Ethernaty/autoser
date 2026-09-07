from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, case, delete, exists, func, or_, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import guard_against_sqli, sanitize_text
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.membership import Membership, MembershipRole
from app.models.order import Order, OrderStatus
from app.models.work_order_assignee import WorkOrderAssignee
from app.models.order_line import OrderLine, OrderLineType
from app.models.payment import Payment, PaymentMethod
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.order_line_repository import OrderLineRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.work_order_registry import WorkOrderRegistry
from app.repositories.payment_repository import PaymentRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.audit_decorator import audit
from app.services.audit_log_service import AuditLogService
from app.services.base_service import BaseService


_MONEY_QUANT = Decimal("0.01")
_WORK_ORDER_TIMELINE_ACTIONS = {
    "work_order_created",
    "work_order_status_changed",
    "work_order_total_amount_changed",
    "work_order_lines_changed",
    "work_order_payment_recorded",
    "work_order_payment_voided",
    "work_order_cancelled",
    "work_order_assignee_changed",
    "work_order_vehicle_changed",
    "work_order_comment_added",
}


@dataclass(frozen=True)
class WorkOrderFinancials:
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal


@dataclass(frozen=True)
class WorkOrderTimelineEntry:
    id: UUID
    work_order_id: UUID
    action: str
    message: str
    user_id: UUID
    actor_email: str | None
    actor_role: str | None
    created_at: datetime


@dataclass(frozen=True)
class WorkOrderRelationStats:
    total_count: int
    active_count: int
    last_activity_at: datetime | None


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
        self, *, q: str | None, status_scope: str = "all", assignee_scope: str = "all",
        limit: int, offset: int, payment_scope: str = "all", date_from: datetime | None = None,
        date_to: datetime | None = None, sort: str = "updated_desc", overdue: bool = False,
    ) -> tuple[list[Order], int]:
        self._validate_pagination(limit=limit, offset=offset)
        filters = dict(q=q.strip()[:100] if q else None, status_scope=status_scope, assignee_scope=assignee_scope,
                       payment_scope=payment_scope, date_from=date_from, date_to=date_to, overdue=overdue)
        def read_op(db: Session):
            repo = WorkOrderRegistry(db=db, tenant_id=self.tenant_id)
            return repo.page(limit=limit, offset=offset, sort=sort, **filters), repo.totals(**filters)["count"]
        return await self.execute_read(read_op)

    async def get_registry_totals(self, **filters) -> dict[str, Any]:
        def read_op(db: Session):
            return WorkOrderRegistry(db=db, tenant_id=self.tenant_id).totals(**filters)
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
        assigned_user_ids: list[UUID] | None = None,
        mileage: int | None = None,
        due_at: datetime | None = None,
        estimated_amount: Decimal | None = None,
        diagnosis: str | None = None,
        intake_notes: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> Order:
        normalized_description = self._normalize_description(description)
        normalized_total = self._normalize_total_amount_for_intake(total_amount)
        normalized_status = self._normalize_status(status)
        normalized_assignee_ids = self._normalize_assignee_ids(
            assigned_user_ids if assigned_user_ids is not None else ([assigned_user_id] if assigned_user_id is not None else [])
        )
        normalized_attachments = self._normalize_attachments(attachments or [])

        def write_op(db: Session) -> Order:
            if normalized_status in {OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED}:
                raise AppError(
                    status_code=400,
                    code="invalid_initial_status",
                    message="Work order can be created only in new or in_progress status",
                )
            self._assert_client_exists(db=db, client_id=client_id)
            self._assert_vehicle_link(db=db, client_id=client_id, vehicle_id=vehicle_id)
            self._assert_assignees_valid(db=db, assigned_user_ids=normalized_assignee_ids)

            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
                    {"lock_key": f"work_order_number:{self.tenant_id}"},
                )
            next_order_number = repo.get_next_order_number()
            order = repo.create(
                order_number=next_order_number,
                client_id=client_id,
                vehicle_id=vehicle_id,
                assigned_user_id=normalized_assignee_ids[0] if normalized_assignee_ids else None,
                description=normalized_description,
                mileage=mileage,
                due_at=due_at,
                estimated_amount=estimated_amount,
                diagnosis=diagnosis,
                intake_notes=intake_notes,
                attachments=normalized_attachments,
                total_amount=normalized_total,
                status=normalized_status,
            )
            self._replace_assignees_in_tx(
                db=db,
                work_order_id=order.id,
                assigned_user_ids=normalized_assignee_ids,
            )
            self._write_work_order_event(
                db=db,
                work_order_id=order.id,
                action="work_order_created",
                message="Work order created",
                metadata={
                    "status": normalized_status.value,
                    "total_amount": str(normalized_total),
                    "client_id": str(client_id),
                    "vehicle_id": str(vehicle_id),
                    "assigned_user_ids": [str(user_id) for user_id in normalized_assignee_ids],
                },
            )
            return order

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
        assigned_user_ids: list[UUID] | None = None,
        mileage: int | None = None,
        due_at: datetime | None = None,
        estimated_amount: Decimal | None = None,
        diagnosis: str | None = None,
        intake_notes: str | None = None,
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
        if assigned_user_ids is not None:
            updates["assigned_user_ids"] = self._normalize_assignee_ids(assigned_user_ids)
        elif assigned_user_id is not None:
            updates["assigned_user_ids"] = self._normalize_assignee_ids([assigned_user_id])
        if mileage is not None:
            updates["mileage"] = mileage
        if due_at is not None:
            updates["due_at"] = due_at
        if estimated_amount is not None:
            updates["estimated_amount"] = self._normalize_money(estimated_amount, field="estimated_amount")
        if diagnosis is not None:
            updates["diagnosis"] = sanitize_text(diagnosis, max_length=5000) or None
        if intake_notes is not None:
            updates["intake_notes"] = sanitize_text(intake_notes, max_length=5000) or None

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> UUID:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")

            previous_status = current.status
            previous_total_amount = Decimal(current.total_amount).quantize(_MONEY_QUANT)
            paid_amount = self._paid_amount_in_tx(db=db, work_order_id=work_order_id)
            effective_total_amount = (
                Decimal(updates["total_amount"]).quantize(_MONEY_QUANT)
                if "total_amount" in updates
                else Decimal(current.total_amount).quantize(_MONEY_QUANT)
            )
            remaining_amount = max(effective_total_amount - paid_amount, Decimal("0.00")).quantize(_MONEY_QUANT)

            if "total_amount" in updates and paid_amount > effective_total_amount:
                raise AppError(
                    status_code=400,
                    code="total_below_paid_amount",
                    message="Total amount cannot be lower than already paid amount",
                    details={
                        "paid_amount": str(paid_amount),
                        "requested_total_amount": str(effective_total_amount),
                    },
                )

            requested_status = updates.get("status")
            if isinstance(requested_status, OrderStatus):
                self._assert_status_transition(current=current.status, target=requested_status)

            effective_status = requested_status if isinstance(requested_status, OrderStatus) else current.status

            if effective_status == OrderStatus.COMPLETED_PAID and remaining_amount > Decimal("0.00"):
                raise AppError(
                    status_code=400,
                    code="cannot_mark_completed_paid",
                    message="Work order cannot be marked completed_paid while remaining amount is greater than zero",
                    details={"remaining_amount": str(remaining_amount)},
                )

            if effective_status == OrderStatus.COMPLETED_UNPAID and remaining_amount <= Decimal("0.00"):
                updates["status"] = OrderStatus.COMPLETED_PAID
                effective_status = OrderStatus.COMPLETED_PAID

            if effective_status == OrderStatus.CANCELLED and paid_amount > Decimal("0.00"):
                raise AppError(
                    status_code=400,
                    code="cannot_cancel_paid_order",
                    message="Cannot cancel work order with recorded payments",
                    details={"paid_amount": str(paid_amount)},
                )

            if "status" not in updates and current.status == OrderStatus.COMPLETED_UNPAID and remaining_amount <= Decimal("0.00"):
                updates["status"] = OrderStatus.COMPLETED_PAID

            if (
                "status" not in updates
                and current.status == OrderStatus.COMPLETED_PAID
                and remaining_amount > Decimal("0.00")
            ):
                raise AppError(
                    status_code=400,
                    code="completed_paid_payment_mismatch",
                    message="completed_paid status requires full payment coverage",
                    details={"remaining_amount": str(remaining_amount)},
                )

            if "vehicle_id" in updates:
                self._assert_vehicle_link(db=db, client_id=current.client_id, vehicle_id=updates["vehicle_id"])  # type: ignore[arg-type]
            previous_assignee_ids = self._list_assignee_ids_in_tx(db=db, work_order_id=work_order_id)
            next_assignee_ids = previous_assignee_ids
            if "assigned_user_ids" in updates:
                requested_assignee_ids = updates.pop("assigned_user_ids")
                if not isinstance(requested_assignee_ids, list):
                    raise AppError(status_code=400, code="invalid_assignees", message="Invalid assignee list")
                self._assert_assignees_valid(db=db, assigned_user_ids=requested_assignee_ids)
                next_assignee_ids = requested_assignee_ids
                updates["assigned_user_id"] = next_assignee_ids[0] if next_assignee_ids else None

            updated = repo.update(work_order_id, **updates)
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")

            if "assigned_user_id" in updates:
                self._replace_assignees_in_tx(
                    db=db,
                    work_order_id=work_order_id,
                    assigned_user_ids=next_assignee_ids,
                )
                if previous_assignee_ids != next_assignee_ids:
                    self._write_work_order_event(
                        db=db,
                        work_order_id=work_order_id,
                        action="work_order_assignee_changed",
                        message="Assignees updated",
                        metadata={
                            "from_assigned_user_ids": [str(user_id) for user_id in previous_assignee_ids],
                            "to_assigned_user_ids": [str(user_id) for user_id in next_assignee_ids],
                        },
                    )

            if "status" in updates and previous_status != updated.status:
                new_status = updated.status
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_status_changed",
                    message=f"Status changed from {previous_status.value} to {new_status.value}",
                    metadata={"from_status": previous_status.value, "to_status": new_status.value},
                )
                if new_status == OrderStatus.CANCELLED:
                    self._write_work_order_event(
                        db=db,
                        work_order_id=work_order_id,
                        action="work_order_cancelled",
                        message="Work order cancelled",
                        metadata={"from_status": previous_status.value},
                    )

            if "total_amount" in updates:
                new_total_amount = Decimal(updated.total_amount).quantize(_MONEY_QUANT)
                if previous_total_amount != new_total_amount:
                    self._write_work_order_event(
                        db=db,
                        work_order_id=work_order_id,
                        action="work_order_total_amount_changed",
                        message=f"Total amount changed from {previous_total_amount} to {new_total_amount}",
                        metadata={
                            "from_total_amount": str(previous_total_amount),
                            "to_total_amount": str(new_total_amount),
                        },
                    )
            return updated.id

        updated_id = await self.execute_write(write_op, idempotent=False)
        return await self.get_work_order(work_order_id=updated_id)

    async def set_status(self, *, work_order_id: UUID, status: OrderStatus) -> Order:
        return await self.update_work_order(work_order_id=work_order_id, status=status)

    @audit(action="close", entity="work_order")
    async def close_work_order(self, *, work_order_id: UUID) -> Order:
        financials = await self.get_financials(work_order_id=work_order_id)
        target_status = (
            OrderStatus.COMPLETED_PAID
            if financials.remaining_amount <= Decimal("0.00")
            else OrderStatus.COMPLETED_UNPAID
        )
        return await self.update_work_order(work_order_id=work_order_id, status=target_status)

    @audit(action="delete", entity="work_order")
    async def delete_work_order(self, *, work_order_id: UUID) -> None:
        def write_op(db: Session) -> None:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            if not repo.delete_by_id(work_order_id):
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")

        await self.execute_write(write_op, idempotent=False)

    @audit(action="update", entity="work_order")
    async def assign_employee(self, *, work_order_id: UUID, assigned_user_id: UUID | None) -> Order:
        assignee_ids = [assigned_user_id] if assigned_user_id is not None else []
        return await self.assign_employees(work_order_id=work_order_id, assigned_user_ids=assignee_ids)

    @audit(action="update", entity="work_order")
    async def assign_employees(self, *, work_order_id: UUID, assigned_user_ids: list[UUID]) -> Order:
        normalized_assignee_ids = self._normalize_assignee_ids(assigned_user_ids)

        def write_op(db: Session) -> UUID:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            previous_assignee_ids = self._list_assignee_ids_in_tx(db=db, work_order_id=work_order_id)
            self._assert_assignees_valid(db=db, assigned_user_ids=normalized_assignee_ids)
            updated = repo.update(
                work_order_id,
                assigned_user_id=normalized_assignee_ids[0] if normalized_assignee_ids else None,
            )
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            self._replace_assignees_in_tx(
                db=db,
                work_order_id=work_order_id,
                assigned_user_ids=normalized_assignee_ids,
            )
            if previous_assignee_ids != normalized_assignee_ids:
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_assignee_changed",
                    message="Assignees updated",
                    metadata={
                        "from_assigned_user_ids": [str(user_id) for user_id in previous_assignee_ids],
                        "to_assigned_user_ids": [str(user_id) for user_id in normalized_assignee_ids],
                    },
                )
            return updated.id

        updated_id = await self.execute_write(write_op, idempotent=False)
        return await self.get_work_order(work_order_id=updated_id)

    @audit(action="update", entity="work_order")
    async def attach_vehicle(self, *, work_order_id: UUID, vehicle_id: UUID) -> Order:
        def write_op(db: Session) -> UUID:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_by_id(work_order_id)
            if current is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            previous_vehicle_id = current.vehicle_id
            self._assert_vehicle_link(db=db, client_id=current.client_id, vehicle_id=vehicle_id)
            updated = repo.update(work_order_id, vehicle_id=vehicle_id)
            if updated is None:
                raise AppError(status_code=404, code="work_order_not_found", message="Work order not found")
            if previous_vehicle_id != updated.vehicle_id:
                previous_label = str(previous_vehicle_id) if previous_vehicle_id is not None else "none"
                next_label = str(updated.vehicle_id) if updated.vehicle_id is not None else "none"
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_vehicle_changed",
                    message=f"Vehicle changed from {previous_label} to {next_label}",
                    metadata={
                        "from_vehicle_id": str(previous_vehicle_id) if previous_vehicle_id is not None else None,
                        "to_vehicle_id": str(updated.vehicle_id) if updated.vehicle_id is not None else None,
                    },
                )
            return updated.id

        updated_id = await self.execute_write(write_op, idempotent=False)
        return await self.get_work_order(work_order_id=updated_id)

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
            previous_total = Decimal(order.total_amount).quantize(_MONEY_QUANT)

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
            new_total = self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_lines_changed",
                message=f"Added line '{normalized_name}' ({normalized_line_type.value})",
                metadata={
                    "change_type": "line_added",
                    "line_id": str(line.id),
                    "line_name": normalized_name,
                    "line_type": normalized_line_type.value,
                    "from_total_amount": str(previous_total),
                    "to_total_amount": str(new_total),
                },
            )
            if previous_total != new_total:
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_total_amount_changed",
                    message=f"Total amount changed from {previous_total} to {new_total}",
                    metadata={
                        "from_total_amount": str(previous_total),
                        "to_total_amount": str(new_total),
                        "reason": "order_line_added",
                        "line_id": str(line.id),
                    },
                )
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
            previous_total = Decimal(order.total_amount).quantize(_MONEY_QUANT)
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            line = repo.get_by_id(line_id)
            if line is None or line.order_id != work_order_id:
                raise AppError(status_code=404, code="order_line_not_found", message="Order line not found")
            previous_line_type = line.line_type.value
            previous_name = line.name
            previous_quantity = Decimal(line.quantity).quantize(_MONEY_QUANT)
            previous_unit_price = Decimal(line.unit_price).quantize(_MONEY_QUANT)
            previous_comment = line.comment

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

            new_total = self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)
            changed_fields: list[str] = []
            if previous_line_type != updated.line_type.value:
                changed_fields.append(f"type: {previous_line_type} -> {updated.line_type.value}")
            if previous_name != updated.name:
                changed_fields.append(f"name: {previous_name} -> {updated.name}")
            if previous_quantity != Decimal(updated.quantity).quantize(_MONEY_QUANT):
                changed_fields.append(
                    f"quantity: {previous_quantity} -> {Decimal(updated.quantity).quantize(_MONEY_QUANT)}"
                )
            if previous_unit_price != Decimal(updated.unit_price).quantize(_MONEY_QUANT):
                changed_fields.append(
                    f"unit price: {previous_unit_price} -> {Decimal(updated.unit_price).quantize(_MONEY_QUANT)}"
                )
            if previous_comment != updated.comment:
                changed_fields.append("comment updated")
            line_update_suffix = "; ".join(changed_fields) if changed_fields else "fields updated"
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_lines_changed",
                message=f"Updated line '{updated.name}': {line_update_suffix}",
                metadata={
                    "change_type": "line_updated",
                    "line_id": str(updated.id),
                    "line_name": updated.name,
                    "changed_fields": changed_fields,
                    "from_total_amount": str(previous_total),
                    "to_total_amount": str(new_total),
                },
            )
            if previous_total != new_total:
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_total_amount_changed",
                    message=f"Total amount changed from {previous_total} to {new_total}",
                    metadata={
                        "from_total_amount": str(previous_total),
                        "to_total_amount": str(new_total),
                        "reason": "order_line_updated",
                        "line_id": str(updated.id),
                    },
                )
            return updated

        return await self.execute_write(write_op, idempotent=False)

    @audit(action="delete", entity="work_order_line")
    async def remove_order_line(self, *, work_order_id: UUID, line_id: UUID) -> None:
        def write_op(db: Session) -> None:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            self._assert_order_lines_editable(order.status)
            previous_total = Decimal(order.total_amount).quantize(_MONEY_QUANT)
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            line = repo.get_by_id(line_id)
            if line is None or line.order_id != work_order_id:
                raise AppError(status_code=404, code="order_line_not_found", message="Order line not found")
            deleted_line_name = line.name
            db.delete(line)
            db.flush()
            new_total = self._recalculate_total_in_tx(db=db, work_order_id=work_order_id)
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_lines_changed",
                message=f"Removed line '{deleted_line_name}'",
                metadata={
                    "change_type": "line_removed",
                    "line_id": str(line_id),
                    "line_name": deleted_line_name,
                    "from_total_amount": str(previous_total),
                    "to_total_amount": str(new_total),
                },
            )
            if previous_total != new_total:
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_total_amount_changed",
                    message=f"Total amount changed from {previous_total} to {new_total}",
                    metadata={
                        "from_total_amount": str(previous_total),
                        "to_total_amount": str(new_total),
                        "reason": "order_line_removed",
                        "line_id": str(line_id),
                    },
                )

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
            if order.status == OrderStatus.CANCELLED:
                raise AppError(
                    status_code=400,
                    code="payment_not_allowed_for_cancelled",
                    message="Cannot create payment for cancelled work order",
                )
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
            payment = repo.create(
                order_id=work_order_id,
                created_by_user_id=self.actor_user_id,
                amount=normalized_amount,
                method=normalized_method,
                paid_at=normalized_paid_at,
                comment=normalized_comment,
                external_ref=normalized_external_ref,
            )
            post_payment_financials = self._financials_in_tx(db=db, order=order)
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_payment_recorded",
                message=f"Payment recorded: {normalized_amount} via {normalized_method.value}",
                metadata={
                    "payment_id": str(payment.id),
                    "amount": str(normalized_amount),
                    "method": normalized_method.value,
                    "paid_amount": str(post_payment_financials.paid_amount),
                    "remaining_amount": str(post_payment_financials.remaining_amount),
                },
            )

            if order.status == OrderStatus.COMPLETED_UNPAID and post_payment_financials.remaining_amount <= Decimal("0.00"):
                order_repo = OrderRepository(db=db, tenant_id=self.tenant_id)
                order_repo.update(work_order_id, status=OrderStatus.COMPLETED_PAID)
                self._write_work_order_event(
                    db=db,
                    work_order_id=work_order_id,
                    action="work_order_status_changed",
                    message=f"Status changed from {OrderStatus.COMPLETED_UNPAID.value} to {OrderStatus.COMPLETED_PAID.value}",
                    metadata={
                        "from_status": OrderStatus.COMPLETED_UNPAID.value,
                        "to_status": OrderStatus.COMPLETED_PAID.value,
                        "reason": "payment_fully_covered_total",
                    },
                )
            return payment

        return await self.execute_write(write_op, idempotent=False)

    async def list_payments(self, *, work_order_id: UUID) -> list[Payment]:
        def read_op(db: Session) -> list[Payment]:
            self._assert_order_exists(db=db, work_order_id=work_order_id)
            repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
            return repo.list_for_order(order_id=work_order_id, include_voided=True)

        return await self.execute_read(read_op)

    async def void_payment(self, *, work_order_id: UUID, payment_id: UUID, reason: str) -> Payment:
        normalized_reason = self._normalize_optional_comment(reason)
        if not normalized_reason:
            raise AppError(status_code=400, code="void_reason_required", message="A reason is required")

        def write_op(db: Session) -> Payment:
            order = self._assert_order_exists(db=db, work_order_id=work_order_id)
            repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
            payment = repo.get_by_id(payment_id)
            if payment is None or payment.order_id != work_order_id:
                raise AppError(status_code=404, code="payment_not_found", message="Payment not found")
            if payment.voided_at is not None:
                raise AppError(status_code=409, code="payment_already_voided", message="Payment is already voided")
            payment.voided_at = datetime.now(UTC)
            db.flush()
            financials = self._financials_in_tx(db=db, order=order)
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_payment_voided",
                message=f"Payment voided: {payment.amount}. Reason: {normalized_reason}",
                metadata={"payment_id": str(payment.id), "amount": str(payment.amount), "reason": normalized_reason},
            )
            if order.status == OrderStatus.COMPLETED_PAID and financials.remaining_amount > Decimal("0.00"):
                OrderRepository(db=db, tenant_id=self.tenant_id).update(work_order_id, status=OrderStatus.COMPLETED_UNPAID)
            db.refresh(payment)
            return payment

        return await self.execute_write(write_op, idempotent=False)

    @staticmethod
    def _normalize_attachments(items: list[dict[str, Any]]) -> list[dict[str, str]]:
        if len(items) > 5:
            raise AppError(status_code=400, code="too_many_attachments", message="No more than 5 photos are allowed")
        result: list[dict[str, str]] = []
        allowed = {"image/png": "data:image/png;base64,", "image/jpeg": "data:image/jpeg;base64,", "image/webp": "data:image/webp;base64,"}
        total_size = 0
        for item in items:
            content_type = str(item.get("content_type", ""))
            data_url = str(item.get("data_url", ""))
            name = sanitize_text(str(item.get("name", "photo")), max_length=120) or "photo"
            if content_type not in allowed or not data_url.startswith(allowed[content_type]):
                raise AppError(status_code=400, code="invalid_attachment", message="Only PNG, JPEG and WebP photos are supported")
            total_size += len(data_url)
            if len(data_url) > 700_000 or total_size > 2_000_000:
                raise AppError(status_code=400, code="attachment_too_large", message="Photo attachments are too large")
            result.append({"id": str(uuid4()), "name": name, "content_type": content_type, "data_url": data_url, "created_at": datetime.now(UTC).isoformat()})
        return result

    async def get_assignee_ids(self, *, work_order_id: UUID) -> list[UUID]:
        mapping = await self.get_assignee_ids_map(work_order_ids=[work_order_id])
        return mapping.get(work_order_id, [])

    async def get_assignee_ids_map(self, *, work_order_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        unique_ids = list(dict.fromkeys(work_order_ids))
        if not unique_ids:
            return {}

        def read_op(db: Session) -> dict[UUID, list[UUID]]:
            rows = db.execute(
                select(WorkOrderAssignee.order_id, WorkOrderAssignee.user_id)
                .where(
                    WorkOrderAssignee.tenant_id == self.tenant_id,
                    WorkOrderAssignee.order_id.in_(unique_ids),
                )
                .order_by(WorkOrderAssignee.created_at.asc())
            ).all()
            result: dict[UUID, list[UUID]] = {work_order_id: [] for work_order_id in unique_ids}
            for order_id, user_id in rows:
                result.setdefault(order_id, []).append(user_id)
            return result

        return await self.execute_read(read_op)

    async def list_work_order_timeline(
        self,
        *,
        work_order_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkOrderTimelineEntry]:
        safe_limit = max(1, min(200, int(limit)))
        safe_offset = max(0, int(offset))

        def read_op(db: Session) -> list[WorkOrderTimelineEntry]:
            self._assert_order_exists(db=db, work_order_id=work_order_id)
            repo = AuditLogRepository(db=db, tenant_id=self.tenant_id)
            rows = repo.list_entity_logs(entity="work_order", entity_id=work_order_id, limit=safe_limit, offset=safe_offset)
            timeline_rows = [item for item in rows if item.action in _WORK_ORDER_TIMELINE_ACTIONS]
            user_ids = {item.user_id for item in timeline_rows}
            actor_map: dict[UUID, tuple[str | None, str | None]] = {}
            if user_ids:
                actor_rows = db.execute(
                    select(User.id, User.email, Membership.role)
                    .select_from(User)
                    .join(
                        Membership,
                        and_(Membership.user_id == User.id, Membership.tenant_id == self.tenant_id),
                        isouter=True,
                    )
                    .where(User.id.in_(user_ids))
                ).all()
                for user_id, email, role in actor_rows:
                    actor_map[user_id] = (
                        str(email) if email is not None else None,
                        role.value if isinstance(role, MembershipRole) else str(role) if role is not None else None,
                    )

            result: list[WorkOrderTimelineEntry] = []
            for item in timeline_rows:
                metadata = item.metadata_json if isinstance(item.metadata_json, dict) else {}
                message = metadata.get("message") if isinstance(metadata.get("message"), str) else item.action
                actor_email, actor_role = actor_map.get(item.user_id, (None, None))
                result.append(
                    WorkOrderTimelineEntry(
                        id=item.id,
                        work_order_id=item.entity_id or work_order_id,
                        action=item.action,
                        message=message,
                        user_id=item.user_id,
                        actor_email=actor_email,
                        actor_role=actor_role,
                        created_at=item.created_at,
                    )
                )
            return result

        return await self.execute_read(read_op)

    @audit(action="update", entity="work_order")
    async def add_timeline_comment(self, *, work_order_id: UUID, comment: str) -> None:
        normalized_comment = self._normalize_optional_comment(comment)
        if not normalized_comment:
            raise AppError(status_code=400, code="invalid_comment", message="Comment is required")

        def write_op(db: Session) -> None:
            self._assert_order_exists(db=db, work_order_id=work_order_id)
            self._write_work_order_event(
                db=db,
                work_order_id=work_order_id,
                action="work_order_comment_added",
                message=normalized_comment,
                metadata={"comment": normalized_comment},
            )

        await self.execute_write(write_op, idempotent=False)

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

    async def get_order_lines_map(self, *, work_order_ids: list[UUID]) -> dict[UUID, list[OrderLine]]:
        if not work_order_ids:
            return {}

        def read_op(db: Session) -> dict[UUID, list[OrderLine]]:
            repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
            lines = repo.list_for_orders(order_ids=work_order_ids)
            result: dict[UUID, list[OrderLine]] = {work_order_id: [] for work_order_id in work_order_ids}
            for line in lines:
                result.setdefault(line.order_id, []).append(line)
            return result

        return await self.execute_read(read_op)

    async def get_client_relation_stats(self, *, client_ids: list[UUID]) -> dict[UUID, WorkOrderRelationStats]:
        if not client_ids:
            return {}

        def read_op(db: Session) -> dict[UUID, WorkOrderRelationStats]:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            raw_map = repo.stats_by_client_ids(client_ids=client_ids)
            return {
                entity_id: WorkOrderRelationStats(
                    total_count=total_count,
                    active_count=active_count,
                    last_activity_at=last_activity_at,
                )
                for entity_id, (total_count, active_count, last_activity_at) in raw_map.items()
            }

        return await self.execute_read(read_op)

    async def get_client_financials(self, *, client_id: UUID) -> dict[str, Decimal]:
        def read_op(db: Session) -> dict[str, Decimal]:
            rows = WorkOrderRegistry(db=db, tenant_id=self.tenant_id).selection().where(Order.client_id == client_id).subquery()
            paid, debt = db.execute(select(
                func.coalesce(func.sum(rows.c.paid_amount), 0),
                func.coalesce(func.sum(case((rows.c.status != OrderStatus.CANCELLED, rows.c.remaining_amount), else_=0)), 0),
            )).one()
            return {"total_paid": Decimal(paid), "total_debt": Decimal(debt)}

        return await self.execute_read(read_op)

    async def get_vehicle_relation_stats(self, *, vehicle_ids: list[UUID]) -> dict[UUID, WorkOrderRelationStats]:
        if not vehicle_ids:
            return {}

        def read_op(db: Session) -> dict[UUID, WorkOrderRelationStats]:
            repo = OrderRepository(db=db, tenant_id=self.tenant_id)
            raw_map = repo.stats_by_vehicle_ids(vehicle_ids=vehicle_ids)
            return {
                entity_id: WorkOrderRelationStats(
                    total_count=total_count,
                    active_count=active_count,
                    last_activity_at=last_activity_at,
                )
                for entity_id, (total_count, active_count, last_activity_at) in raw_map.items()
            }

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
                        Order.status.in_([OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED]),
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

    async def get_dashboard_analytics(
        self,
        *,
        months: int = 12,
        status_scope: str = "all",
        assignee_scope: str = "all",
    ) -> dict[str, Any]:
        safe_months = max(3, min(24, int(months)))
        normalized_status_scope = self._normalize_dashboard_status_scope(status_scope)
        normalized_assignee_scope = self._normalize_dashboard_assignee_scope(assignee_scope)

        def month_start(value: datetime) -> datetime:
            return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def shift_month(value: datetime, delta: int) -> datetime:
            year = value.year + ((value.month - 1 + delta) // 12)
            month = ((value.month - 1 + delta) % 12) + 1
            return value.replace(year=year, month=month)

        def read_op(db: Session) -> dict[str, Any]:
            now = datetime.now(UTC)
            current_month = month_start(now)
            month_range = [shift_month(current_month, -(safe_months - 1 - idx)) for idx in range(safe_months)]
            oldest_month = month_range[0]
            next_month = shift_month(current_month, 1)
            last_30_days = now - timedelta(days=30)
            last_180_days = now - timedelta(days=180)

            order_scope_criteria = self._build_dashboard_order_scope_criteria(
                status_scope=normalized_status_scope,
                assignee_scope=normalized_assignee_scope,
            )
            scoped_order_conditions = [Order.tenant_id == self.tenant_id, *order_scope_criteria]

            clients_total = int(
                db.execute(
                    select(func.count()).select_from(Client).where(
                        Client.tenant_id == self.tenant_id,
                    )
                ).scalar_one()
            )
            work_orders_total = int(
                db.execute(
                    select(func.count()).select_from(Order).where(
                        *scoped_order_conditions,
                    )
                ).scalar_one()
            )
            open_work_orders_count = int(
                db.execute(
                    select(func.count()).select_from(Order).where(
                        *scoped_order_conditions,
                        Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS]),
                    )
                ).scalar_one()
            )
            closed_work_orders_count = int(
                db.execute(
                    select(func.count()).select_from(Order).where(
                        *scoped_order_conditions,
                        Order.status.in_([OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED]),
                    )
                ).scalar_one()
            )
            paid_amount_30d = Decimal(
                db.execute(
                    select(func.coalesce(func.sum(Payment.amount), 0))
                    .select_from(Payment)
                    .join(
                        Order,
                        and_(
                            Order.id == Payment.order_id,
                            Order.tenant_id == self.tenant_id,
                        ),
                    )
                    .where(
                        Payment.tenant_id == self.tenant_id,
                        Payment.voided_at.is_(None),
                        Payment.paid_at >= last_30_days,
                        *order_scope_criteria,
                    )
                ).scalar_one()
                or 0
            ).quantize(_MONEY_QUANT)

            order_month_rows = db.execute(
                select(
                    func.date_trunc("month", Order.created_at).label("bucket"),
                    func.count(Order.id).label("orders_count"),
                    func.coalesce(func.sum(Order.total_amount), 0).label("order_amount"),
                )
                .where(
                    *scoped_order_conditions,
                    Order.created_at >= oldest_month,
                    Order.created_at < next_month,
                )
                .group_by("bucket")
            ).all()
            order_month_map = {
                row.bucket.date().replace(day=1): {
                    "orders_count": int(row.orders_count or 0),
                    "order_amount": Decimal(row.order_amount or 0).quantize(_MONEY_QUANT),
                }
                for row in order_month_rows
                if row.bucket is not None
            }

            client_month_rows = db.execute(
                select(
                    func.date_trunc("month", Client.created_at).label("bucket"),
                    func.count(Client.id).label("clients_count"),
                )
                .where(
                    Client.tenant_id == self.tenant_id,
                    Client.created_at >= oldest_month,
                    Client.created_at < next_month,
                )
                .group_by("bucket")
            ).all()
            client_month_map = {
                row.bucket.date().replace(day=1): int(row.clients_count or 0)
                for row in client_month_rows
                if row.bucket is not None
            }

            payment_month_rows = db.execute(
                select(
                    func.date_trunc("month", Payment.paid_at).label("bucket"),
                    func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
                )
                .select_from(Payment)
                .join(
                    Order,
                    and_(
                        Order.id == Payment.order_id,
                        Order.tenant_id == self.tenant_id,
                    ),
                )
                .where(
                    Payment.tenant_id == self.tenant_id,
                    Payment.voided_at.is_(None),
                    Payment.paid_at >= oldest_month,
                    Payment.paid_at < next_month,
                    *order_scope_criteria,
                )
                .group_by("bucket")
            ).all()
            payment_month_map = {
                row.bucket.date().replace(day=1): Decimal(row.paid_amount or 0).quantize(_MONEY_QUANT)
                for row in payment_month_rows
                if row.bucket is not None
            }

            client_source_rows = db.execute(
                select(
                    func.coalesce(func.nullif(func.trim(Client.source), ""), "unknown").label("source"),
                    func.count(Client.id).label("clients_count"),
                )
                .where(Client.tenant_id == self.tenant_id)
                .group_by("source")
                .order_by(func.count(Client.id).desc())
                .limit(6)
            ).all()
            client_sources = [
                {
                    "source": str(row.source),
                    "clients_count": int(row.clients_count or 0),
                }
                for row in client_source_rows
            ]

            service_rows = db.execute(
                select(
                    func.lower(OrderLine.name).label("name_key"),
                    func.max(OrderLine.name).label("display_name"),
                    func.count(OrderLine.id).label("usage_count"),
                )
                .select_from(OrderLine)
                .join(
                    Order,
                    and_(
                        Order.id == OrderLine.order_id,
                        Order.tenant_id == self.tenant_id,
                    ),
                )
                .where(
                    OrderLine.tenant_id == self.tenant_id,
                    OrderLine.created_at >= last_180_days,
                    *order_scope_criteria,
                )
                .group_by("name_key")
                .order_by(func.count(OrderLine.id).desc())
                .limit(6)
            ).all()
            popular_services = [
                {
                    "name": str(row.display_name),
                    "usage_count": int(row.usage_count or 0),
                }
                for row in service_rows
                if row.display_name
            ]

            paid_amount_subquery = (
                select(
                    Payment.order_id.label("order_id"),
                    func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
                )
                .where(
                    Payment.tenant_id == self.tenant_id,
                    Payment.voided_at.is_(None),
                )
                .group_by(Payment.order_id)
                .subquery()
            )
            remaining_expr = Order.total_amount - func.coalesce(paid_amount_subquery.c.paid_amount, 0)

            unpaid_orders_count = int(
                db.execute(
                    select(func.count())
                    .select_from(Order)
                    .outerjoin(paid_amount_subquery, paid_amount_subquery.c.order_id == Order.id)
                    .where(
                        *scoped_order_conditions,
                        Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED_UNPAID]),
                        remaining_expr > 0,
                    )
                ).scalar_one()
            )

            problematic_order_rows = db.execute(
                select(
                    Order.id,
                    Order.description,
                    Order.status,
                    remaining_expr.label("remaining_amount"),
                    Order.created_at,
                )
                .select_from(Order)
                .outerjoin(paid_amount_subquery, paid_amount_subquery.c.order_id == Order.id)
                .where(
                    *scoped_order_conditions,
                    Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED_UNPAID]),
                    remaining_expr > 0,
                )
                .order_by(remaining_expr.desc(), Order.created_at.asc())
                .limit(6)
            ).all()
            problematic_orders = [
                {
                    "id": row.id,
                    "description": row.description,
                    "status": row.status.value if isinstance(row.status, OrderStatus) else str(row.status),
                    "remaining_amount": Decimal(row.remaining_amount or 0).quantize(_MONEY_QUANT),
                    "created_at": row.created_at,
                }
                for row in problematic_order_rows
            ]

            seasonality_monthly = []
            revenue_monthly = []
            for month_point in month_range:
                month_key = month_point.date().replace(day=1)
                period = month_point.strftime("%Y-%m")
                month_orders = order_month_map.get(month_key, {"orders_count": 0, "order_amount": Decimal("0.00")})
                seasonality_monthly.append(
                    {
                        "period": period,
                        "orders_count": int(month_orders["orders_count"]),
                        "clients_count": int(client_month_map.get(month_key, 0)),
                    }
                )
                revenue_monthly.append(
                    {
                        "period": period,
                        "paid_amount": payment_month_map.get(month_key, Decimal("0.00")).quantize(_MONEY_QUANT),
                        "order_amount": Decimal(month_orders["order_amount"]).quantize(_MONEY_QUANT),
                    }
                )

            weekday_start = now - timedelta(days=30)
            weekday_rows = db.execute(
                select(
                    func.extract("dow", Order.created_at).label("dow"),
                    func.count(Order.id).label("orders_count"),
                )
                .where(
                    *scoped_order_conditions,
                    Order.created_at >= weekday_start,
                )
                .group_by("dow")
            ).all()
            weekday_map = {int(row.dow): int(row.orders_count or 0) for row in weekday_rows if row.dow is not None}
            # PostgreSQL dow: 0=Sunday ... 6=Saturday
            weekdays = [
                ("mon", 1),
                ("tue", 2),
                ("wed", 3),
                ("thu", 4),
                ("fri", 5),
                ("sat", 6),
                ("sun", 0),
            ]
            load_by_weekday = [
                {"weekday": label, "orders_count": int(weekday_map.get(dow, 0))}
                for label, dow in weekdays
            ]

            return {
                "generated_at": now,
                "clients_total": clients_total,
                "work_orders_total": work_orders_total,
                "open_work_orders_count": open_work_orders_count,
                "closed_work_orders_count": closed_work_orders_count,
                "paid_amount_30d": paid_amount_30d,
                "unpaid_orders_count": unpaid_orders_count,
                "seasonality_monthly": seasonality_monthly,
                "load_by_weekday": load_by_weekday,
                "revenue_monthly": revenue_monthly,
                "client_sources": client_sources,
                "popular_services": popular_services,
                "problematic_orders": problematic_orders,
            }

        return await self.execute_read(read_op)

    @staticmethod
    def _normalize_dashboard_status_scope(raw_scope: str | None) -> str:
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
    def _normalize_dashboard_assignee_scope(raw_scope: str | None) -> str:
        candidate = str(raw_scope or "all").strip().lower()
        if candidate in {"all", "unassigned"}:
            return candidate
        try:
            return str(UUID(str(raw_scope)))
        except Exception:
            return "all"

    def _build_dashboard_order_scope_criteria(self, *, status_scope: str, assignee_scope: str) -> list[object]:
        criteria: list[object] = []

        if status_scope == "active":
            criteria.append(Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS]))
        elif status_scope == "completed":
            criteria.append(Order.status.in_([OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID]))
        elif status_scope == "cancelled":
            criteria.append(Order.status == OrderStatus.CANCELLED)
        elif status_scope == "completed_unpaid":
            criteria.append(Order.status == OrderStatus.COMPLETED_UNPAID)
        elif status_scope == "new":
            criteria.append(Order.status == OrderStatus.NEW)
        elif status_scope == "in_progress":
            criteria.append(Order.status == OrderStatus.IN_PROGRESS)
        elif status_scope == "completed_paid":
            criteria.append(Order.status == OrderStatus.COMPLETED_PAID)

        if assignee_scope == "unassigned":
            criteria.append(Order.assigned_user_id.is_(None))
            criteria.append(
                ~exists(
                    select(1).where(
                        WorkOrderAssignee.tenant_id == self.tenant_id,
                        WorkOrderAssignee.order_id == Order.id,
                    )
                )
            )
        elif assignee_scope != "all":
            assignee_id = UUID(assignee_scope)
            criteria.append(
                or_(
                    Order.assigned_user_id == assignee_id,
                    exists(
                        select(1).where(
                            WorkOrderAssignee.tenant_id == self.tenant_id,
                            WorkOrderAssignee.order_id == Order.id,
                            WorkOrderAssignee.user_id == assignee_id,
                        )
                    ),
                )
            )

        return criteria

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
        self._assert_assignees_valid(db=db, assigned_user_ids=[assigned_user_id])

    def _assert_assignees_valid(self, *, db: Session, assigned_user_ids: list[UUID]) -> None:
        if not assigned_user_ids:
            return
        memberships = db.execute(
            select(Membership).where(
                Membership.tenant_id == self.tenant_id,
                Membership.user_id.in_(assigned_user_ids),
                Membership.role.in_(
                    [MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER, MembershipRole.EMPLOYEE]
                ),
            )
        ).scalars().all()
        resolved_user_ids = {item.user_id for item in memberships}
        missing_user_ids = [user_id for user_id in assigned_user_ids if user_id not in resolved_user_ids]
        if missing_user_ids:
            raise AppError(status_code=404, code="employee_not_found", message="Employee not found in workspace")

    def _list_assignee_ids_in_tx(self, *, db: Session, work_order_id: UUID) -> list[UUID]:
        rows = db.execute(
            select(WorkOrderAssignee.user_id)
            .where(
                WorkOrderAssignee.tenant_id == self.tenant_id,
                WorkOrderAssignee.order_id == work_order_id,
            )
            .order_by(WorkOrderAssignee.created_at.asc())
        ).scalars().all()
        return list(rows)

    def _replace_assignees_in_tx(self, *, db: Session, work_order_id: UUID, assigned_user_ids: list[UUID]) -> None:
        db.execute(
            delete(WorkOrderAssignee).where(
                WorkOrderAssignee.tenant_id == self.tenant_id,
                WorkOrderAssignee.order_id == work_order_id,
            )
        )
        for user_id in assigned_user_ids:
            db.add(
                WorkOrderAssignee(
                    tenant_id=self.tenant_id,
                    order_id=work_order_id,
                    user_id=user_id,
                )
            )
        db.flush()

    def _assert_status_transition(self, *, current: OrderStatus, target: OrderStatus) -> None:
        if current == target:
            return
        allowed: dict[OrderStatus, set[OrderStatus]] = {
            OrderStatus.NEW: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
            OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED},
            OrderStatus.COMPLETED_UNPAID: {OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED},
            OrderStatus.COMPLETED_PAID: {OrderStatus.CANCELLED},
            OrderStatus.CANCELLED: set(),
        }
        if target not in allowed.get(current, set()):
            raise AppError(
                status_code=400,
                code="invalid_status_transition",
                message="Invalid work-order status transition",
                details={"from": current.value, "to": target.value},
            )

    def _assert_order_lines_editable(self, status: OrderStatus) -> None:
        if status in {OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID, OrderStatus.CANCELLED}:
            raise AppError(
                status_code=400,
                code="work_order_closed",
                message="Cannot modify lines for closed work order",
            )

    def _recalculate_total_in_tx(self, *, db: Session, work_order_id: UUID) -> Decimal:
        line_repo = OrderLineRepository(db=db, tenant_id=self.tenant_id)
        lines = line_repo.list_for_order(order_id=work_order_id)
        total = sum((Decimal(line.line_total) for line in lines), Decimal("0.00")).quantize(_MONEY_QUANT)
        order_repo = OrderRepository(db=db, tenant_id=self.tenant_id)
        order_repo.update(work_order_id, total_amount=total)
        return total

    def _write_work_order_event(
        self,
        *,
        db: Session,
        work_order_id: UUID,
        action: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.actor_user_id is None:
            return
        payload = {"message": message}
        if metadata:
            payload.update(metadata)
        repo = AuditLogRepository(db=db, tenant_id=self.tenant_id)
        repo.create_log(
            user_id=self.actor_user_id,
            action=action,
            entity="work_order",
            entity_id=work_order_id,
            metadata=payload,
        )

    def _financials_in_tx(self, *, db: Session, order: Order) -> WorkOrderFinancials:
        pay_repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
        paid = pay_repo.sum_paid_for_order(order_id=order.id)
        total = Decimal(order.total_amount).quantize(_MONEY_QUANT)
        remaining = max(total - paid, Decimal("0.00")).quantize(_MONEY_QUANT)
        return WorkOrderFinancials(total_amount=total, paid_amount=paid, remaining_amount=remaining)

    def _paid_amount_in_tx(self, *, db: Session, work_order_id: UUID) -> Decimal:
        pay_repo = PaymentRepository(db=db, tenant_id=self.tenant_id)
        return pay_repo.sum_paid_for_order(order_id=work_order_id).quantize(_MONEY_QUANT)

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
    def _normalize_assignee_ids(values: list[UUID] | None) -> list[UUID]:
        if not values:
            return []
        unique_values: list[UUID] = []
        seen: set[UUID] = set()
        for item in values:
            if item in seen:
                continue
            unique_values.append(item)
            seen.add(item)
        return unique_values

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
    def _normalize_total_amount_for_intake(value: Decimal) -> Decimal:
        try:
            normalized = Decimal(value).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AppError(status_code=400, code="invalid_total_amount", message="Invalid total_amount") from exc
        if normalized < 0:
            raise AppError(status_code=400, code="invalid_total_amount", message="Invalid total_amount")
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

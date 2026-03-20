from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from models.work_item import WorkItem
from models.work_order import (
    STATUS_ACCEPTED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_LABELS,
    WorkOrder,
)
from repositories.client_repo import ClientRepository
from repositories.employee_repo import EmployeeRepository
from repositories.vehicle_repo import VehicleRepository
from repositories.work_item_repo import WorkItemRepository
from repositories.work_order_repo import WorkOrderRepository
from services.errors import BusinessRuleError, NotFoundError, ValidationError
from services.validators import (
    normalize_optional_text,
    require_non_empty,
    validate_id,
    validate_money,
)


ALLOWED_STATUS_TRANSITIONS = {
    STATUS_ACCEPTED: {STATUS_IN_PROGRESS, STATUS_COMPLETED},
    STATUS_IN_PROGRESS: {STATUS_COMPLETED},
    STATUS_COMPLETED: set(),
}


@dataclass
class WorkOrderListRow:
    id: int
    created_at: str
    client_name: str
    vehicle_name: str
    status: str
    status_label: str
    total_amount: float


@dataclass
class WorkItemRow:
    id: int
    name: str
    price: float
    employee_name: str


class OrderService:
    def __init__(
        self,
        order_repo: WorkOrderRepository | None = None,
        item_repo: WorkItemRepository | None = None,
        client_repo: ClientRepository | None = None,
        vehicle_repo: VehicleRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
    ):
        self.order_repo = order_repo or WorkOrderRepository()
        self.item_repo = item_repo or WorkItemRepository()
        self.client_repo = client_repo or ClientRepository()
        self.vehicle_repo = vehicle_repo or VehicleRepository()
        self.employee_repo = employee_repo or EmployeeRepository()

    def list_orders(self, search: str = "") -> List[WorkOrderListRow]:
        rows = self.order_repo.get_all_with_details((search or "").strip())
        result: List[WorkOrderListRow] = []
        for row in rows:
            status = row["status"]
            result.append(
                WorkOrderListRow(
                    id=row["id"],
                    created_at=row["created_at"] or "",
                    client_name=row["client_name"] or "—",
                    vehicle_name=row["vehicle_name"] or "—",
                    status=status,
                    status_label=STATUS_LABELS.get(status, status),
                    total_amount=float(row["total_amount"] or 0),
                )
            )
        return result

    def get_order(self, order_id: int) -> WorkOrder:
        order = self.order_repo.get_by_id(validate_id(order_id, "Заказ-наряд"))
        if not order:
            raise NotFoundError("Заказ-наряд не найден.")
        return order

    def create_order(self, *, client_id: int, vehicle_id: int, status: str, notes: str = "") -> WorkOrder:
        validate_id(client_id, "Клиент")
        validate_id(vehicle_id, "Автомобиль")

        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise BusinessRuleError("Нельзя создать заказ без клиента.")

        vehicle = self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise BusinessRuleError("Нельзя создать заказ без автомобиля.")
        if vehicle.client_id != client_id:
            raise BusinessRuleError("Выбранный автомобиль не принадлежит выбранному клиенту.")

        if status not in STATUS_LABELS:
            raise ValidationError("Указан некорректный статус заказа.")

        order = WorkOrder(
            client_id=client_id,
            vehicle_id=vehicle_id,
            status=status,
            notes=normalize_optional_text(notes),
        )
        return self.order_repo.create(order)

    def delete_order(self, order_id: int) -> None:
        self.get_order(order_id)
        self.order_repo.delete(order_id)

    def update_status(self, order_id: int, new_status: str) -> WorkOrder:
        if new_status not in STATUS_LABELS:
            raise ValidationError("Указан некорректный статус заказа.")

        order = self.get_order(order_id)
        current_status = order.status
        if current_status == new_status:
            return order

        allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise BusinessRuleError(
                f"Недопустимый переход статуса: {STATUS_LABELS.get(current_status, current_status)} -> "
                f"{STATUS_LABELS.get(new_status, new_status)}."
            )

        order.status = new_status
        return self.order_repo.update(order)

    def list_items(self, order_id: int) -> List[WorkItemRow]:
        validate_id(order_id, "Заказ-наряд")
        rows = self.item_repo.get_by_order_id_with_employee(order_id)
        return [
            WorkItemRow(
                id=row["id"],
                name=row["name"],
                price=float(row["price"] or 0),
                employee_name=row["employee_name"] or "—",
            )
            for row in rows
        ]

    def add_work_item(
        self,
        *,
        order_id: int,
        name: str,
        price: float,
        employee_id: Optional[int],
    ) -> WorkItem:
        order = self.get_order(order_id)
        if order.status == STATUS_COMPLETED:
            raise BusinessRuleError("Нельзя добавлять работы в завершённый заказ.")

        employee = None
        if employee_id:
            employee = self.employee_repo.get_by_id(validate_id(employee_id, "Исполнитель"))
            if not employee:
                raise BusinessRuleError("Выбран несуществующий сотрудник.")

        item = WorkItem(
            work_order_id=order.id,
            name=require_non_empty(name, "Название работы"),
            price=validate_money(price, "Цена работы"),
            employee_id=employee.id if employee else None,
        )
        created = self.item_repo.create(item)
        self.order_repo.update_total(order.id)
        return created

    def delete_work_item(self, *, order_id: int, item_id: int) -> None:
        order = self.get_order(order_id)
        if order.status == STATUS_COMPLETED:
            raise BusinessRuleError("Нельзя удалять работы из завершённого заказа.")

        item = self.item_repo.get_by_id(validate_id(item_id, "Работа"))
        if not item or item.work_order_id != order.id:
            raise NotFoundError("Работа не найдена в этом заказе.")

        self.item_repo.delete(item_id)
        self.order_repo.update_total(order.id)

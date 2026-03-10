from __future__ import annotations

from typing import List

from models.employee import Employee
from repositories.employee_repo import EmployeeRepository
from services.errors import NotFoundError
from services.validators import require_non_empty, validate_commission_pct, validate_id


class EmployeeService:
    def __init__(self, repo: EmployeeRepository | None = None):
        self.repo = repo or EmployeeRepository()

    def list_employees(self) -> List[Employee]:
        return self.repo.get_all()

    def get_employee(self, employee_id: int) -> Employee:
        employee = self.repo.get_by_id(validate_id(employee_id, "Сотрудник"))
        if not employee:
            raise NotFoundError("Сотрудник не найден.")
        return employee

    def create_employee(self, *, full_name: str, commission_pct: int) -> Employee:
        employee = Employee(
            full_name=require_non_empty(full_name, "ФИО"),
            commission_pct=validate_commission_pct(commission_pct),
        )
        return self.repo.create(employee)

    def update_employee(self, employee_id: int, *, full_name: str, commission_pct: int) -> Employee:
        employee = self.get_employee(employee_id)
        employee.full_name = require_non_empty(full_name, "ФИО")
        employee.commission_pct = validate_commission_pct(commission_pct)
        return self.repo.update(employee)

    def delete_employee(self, employee_id: int) -> None:
        self.get_employee(employee_id)
        self.repo.delete(employee_id)

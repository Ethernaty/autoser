from contextlib import closing
from typing import List, Optional

from database.connection import get_connection
from models.employee import Employee


class EmployeeRepository:
    def get_all(self) -> List[Employee]:
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT * FROM employees ORDER BY full_name"
            ).fetchall()
        return [Employee.from_row(r) for r in rows]

    def get_by_id(self, emp_id: int) -> Optional[Employee]:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM employees WHERE id = ?",
                (emp_id,),
            ).fetchone()
        return Employee.from_row(row)

    def create(self, emp: Employee) -> Employee:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                "INSERT INTO employees (full_name, commission_pct) VALUES (?, ?)",
                (emp.full_name, emp.commission_pct),
            )
            emp.id = cursor.lastrowid
            conn.commit()
        return emp

    def update(self, emp: Employee) -> Employee:
        with closing(get_connection()) as conn:
            conn.execute(
                "UPDATE employees SET full_name=?, commission_pct=? WHERE id=?",
                (emp.full_name, emp.commission_pct, emp.id),
            )
            conn.commit()
        return emp

    def delete(self, emp_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
            conn.commit()

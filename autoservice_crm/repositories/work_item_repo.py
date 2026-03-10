from contextlib import closing
from typing import List, Optional

from database.connection import get_connection
from models.work_item import WorkItem


class WorkItemRepository:
    def get_by_order_id(self, order_id: int) -> List[WorkItem]:
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT * FROM work_items WHERE work_order_id = ?",
                (order_id,),
            ).fetchall()
        return [WorkItem.from_row(r) for r in rows]

    def get_by_order_id_with_employee(self, order_id: int):
        with closing(get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT
                    wi.*,
                    e.full_name AS employee_name
                FROM work_items wi
                LEFT JOIN employees e ON e.id = wi.employee_id
                WHERE wi.work_order_id = ?
                ORDER BY wi.id
                """,
                (order_id,),
            ).fetchall()
        return rows

    def get_by_id(self, item_id: int) -> Optional[WorkItem]:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM work_items WHERE id = ?",
                (item_id,),
            ).fetchone()
        return WorkItem.from_row(row)

    def create(self, item: WorkItem) -> WorkItem:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO work_items (work_order_id, name, price, employee_id)
                VALUES (?, ?, ?, ?)
                """,
                (item.work_order_id, item.name, item.price, item.employee_id),
            )
            item.id = cursor.lastrowid
            conn.commit()
        return item

    def delete(self, item_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM work_items WHERE id = ?", (item_id,))
            conn.commit()

    def get_completed_by_employee(
        self, employee_id: int, date_from: str = "", date_to: str = ""
    ) -> List[WorkItem]:
        query = """
            SELECT wi.* FROM work_items wi
            JOIN work_orders wo ON wo.id = wi.work_order_id
            WHERE wi.employee_id = ?
              AND wo.status = 'completed'
        """
        params = [employee_id]

        if date_from:
            query += " AND wo.created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND wo.created_at <= ?"
            params.append(date_to + " 23:59:59")

        with closing(get_connection()) as conn:
            rows = conn.execute(query, params).fetchall()
        return [WorkItem.from_row(r) for r in rows]

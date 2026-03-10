from contextlib import closing
from typing import List, Optional

from database.connection import get_connection
from models.work_order import WorkOrder


class WorkOrderRepository:
    def get_all(self, search: str = "") -> List[WorkOrder]:
        with closing(get_connection()) as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    """
                    SELECT wo.* FROM work_orders wo
                    LEFT JOIN clients c ON c.id = wo.client_id
                    WHERE CAST(wo.id AS TEXT) LIKE ?
                       OR c.full_name LIKE ?
                    ORDER BY wo.created_at DESC
                    """,
                    (like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM work_orders ORDER BY created_at DESC"
                ).fetchall()
        return [WorkOrder.from_row(r) for r in rows]

    def get_all_with_details(self, search: str = ""):
        base_query = """
            SELECT
                wo.*,
                c.full_name AS client_name,
                TRIM(
                    COALESCE(v.make, '') || ' ' || COALESCE(v.model, '') ||
                    CASE
                        WHEN COALESCE(v.license_plate, '') = '' THEN ''
                        ELSE ' [' || v.license_plate || ']'
                    END
                ) AS vehicle_name
            FROM work_orders wo
            LEFT JOIN clients c ON c.id = wo.client_id
            LEFT JOIN vehicles v ON v.id = wo.vehicle_id
        """
        with closing(get_connection()) as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    base_query
                    + """
                    WHERE CAST(wo.id AS TEXT) LIKE ?
                       OR c.full_name LIKE ?
                       OR v.make LIKE ?
                       OR v.model LIKE ?
                       OR v.license_plate LIKE ?
                    ORDER BY wo.created_at DESC
                    """,
                    (like, like, like, like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    base_query + " ORDER BY wo.created_at DESC"
                ).fetchall()
        return rows

    def get_by_id(self, order_id: int) -> Optional[WorkOrder]:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM work_orders WHERE id = ?",
                (order_id,),
            ).fetchone()
        return WorkOrder.from_row(row)

    def get_by_client_id(self, client_id: int) -> List[WorkOrder]:
        with closing(get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM work_orders
                WHERE client_id = ?
                ORDER BY created_at DESC
                """,
                (client_id,),
            ).fetchall()
        return [WorkOrder.from_row(r) for r in rows]

    def create(self, order: WorkOrder) -> WorkOrder:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO work_orders (client_id, vehicle_id, status, notes, total_amount)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order.client_id,
                    order.vehicle_id,
                    order.status,
                    order.notes,
                    order.total_amount,
                ),
            )
            order.id = cursor.lastrowid
            conn.commit()
        return order

    def update(self, order: WorkOrder) -> WorkOrder:
        with closing(get_connection()) as conn:
            conn.execute(
                """
                UPDATE work_orders
                SET client_id=?, vehicle_id=?, status=?, notes=?, total_amount=?
                WHERE id=?
                """,
                (
                    order.client_id,
                    order.vehicle_id,
                    order.status,
                    order.notes,
                    order.total_amount,
                    order.id,
                ),
            )
            conn.commit()
        return order

    def update_total(self, order_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute(
                """
                UPDATE work_orders
                SET total_amount = COALESCE(
                    (SELECT SUM(price) FROM work_items WHERE work_order_id = ?), 0
                )
                WHERE id = ?
                """,
                (order_id, order_id),
            )
            conn.commit()

    def delete(self, order_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM work_orders WHERE id = ?", (order_id,))
            conn.commit()

    def count_by_status(self, status: str) -> int:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM work_orders WHERE status = ?",
                (status,),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def total_revenue(self) -> float:
        with closing(get_connection()) as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM work_orders
                WHERE status = 'completed'
                """
            ).fetchone()
        return float(row["total"]) if row else 0.0

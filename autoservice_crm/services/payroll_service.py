from dataclasses import dataclass
from typing import List

from database.connection import get_connection


@dataclass
class PayrollRow:
    employee_id: int
    employee_name: str
    commission_pct: int
    work_count: int
    work_total: float
    payout: float


class PayrollService:
    def calculate(self, date_from: str = "", date_to: str = "") -> List[PayrollRow]:
        conn = get_connection()
        join_conditions = ["wo.id = wi.work_order_id", "wo.status = 'completed'"]
        params: list[str] = []
        if date_from:
            join_conditions.append("wo.created_at >= ?")
            params.append(date_from)
        if date_to:
            join_conditions.append("wo.created_at <= ?")
            params.append(date_to + " 23:59:59")

        join_expr = " AND ".join(join_conditions)
        query = """
            SELECT
                e.id AS employee_id,
                e.full_name AS employee_name,
                e.commission_pct AS commission_pct,
                COUNT(CASE WHEN wo.id IS NOT NULL THEN wi.id END) AS work_count,
                COALESCE(SUM(CASE WHEN wo.id IS NOT NULL THEN wi.price ELSE 0 END), 0) AS work_total
            FROM employees e
            LEFT JOIN work_items wi ON wi.employee_id = e.id
            LEFT JOIN work_orders wo ON
        """
        query += join_expr
        query += """
            GROUP BY e.id, e.full_name, e.commission_pct
            ORDER BY e.full_name
        """

        rows = conn.execute(query, params).fetchall()
        conn.close()

        result: List[PayrollRow] = []
        for row in rows:
            work_total = float(row["work_total"] or 0)
            commission_pct = int(row["commission_pct"])
            payout = round(work_total * commission_pct / 100, 2)
            result.append(
                PayrollRow(
                    employee_id=row["employee_id"],
                    employee_name=row["employee_name"],
                    commission_pct=commission_pct,
                    work_count=row["work_count"],
                    work_total=work_total,
                    payout=payout,
                )
            )
        return result

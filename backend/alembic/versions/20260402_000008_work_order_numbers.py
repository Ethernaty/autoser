"""work_order_numbers

Revision ID: 20260402_000008
Revises: 20260329_000007
Create Date: 2026-04-02 00:00:08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260402_000008"
down_revision = "20260329_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("order_number", sa.Integer(), nullable=True))

    op.execute(
        """
        WITH numbered AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY tenant_id
                    ORDER BY created_at ASC, id ASC
                ) AS seq
            FROM orders
        )
        UPDATE orders AS o
        SET order_number = numbered.seq
        FROM numbered
        WHERE o.id = numbered.id
        """
    )

    op.alter_column("orders", "order_number", nullable=False)
    op.create_unique_constraint(
        "uq_orders_tenant_order_number",
        "orders",
        ["tenant_id", "order_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_orders_tenant_order_number", "orders", type_="unique")
    op.drop_column("orders", "order_number")

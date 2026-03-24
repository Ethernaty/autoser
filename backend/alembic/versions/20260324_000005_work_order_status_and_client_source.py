"""work_order_status_and_client_source

Revision ID: 20260324_000005
Revises: 20260313_000004
Create Date: 2026-03-24 00:00:05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260324_000005"
down_revision = "20260313_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("source", sa.String(length=120), nullable=True))

    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=11),
        type_=sa.String(length=32),
        existing_nullable=False,
    )

    op.execute(
        """
        UPDATE orders
        SET status = CASE
            WHEN status = 'CANCELED' THEN 'CANCELLED'
            WHEN status = 'COMPLETED' THEN
                CASE
                    WHEN COALESCE((
                        SELECT SUM(p.amount)
                        FROM payments p
                        WHERE p.order_id = orders.id
                          AND p.tenant_id = orders.tenant_id
                          AND p.voided_at IS NULL
                    ), 0) >= orders.total_amount
                    THEN 'COMPLETED_PAID'
                    ELSE 'COMPLETED_UNPAID'
                END
            ELSE status
        END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE orders
        SET status = CASE
            WHEN status IN ('COMPLETED_UNPAID', 'COMPLETED_PAID') THEN 'COMPLETED'
            WHEN status = 'CANCELLED' THEN 'CANCELED'
            ELSE status
        END
        """
    )

    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=11),
        existing_nullable=False,
    )

    op.drop_column("clients", "source")

"""work_order_assignees

Revision ID: 20260405_000009
Revises: 20260402_000008
Create Date: 2026-04-05 00:00:09
"""
from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000009"
down_revision = "20260402_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_order_assignees",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "order_id",
            "user_id",
            name="uq_work_order_assignees_tenant_order_user",
        ),
    )
    op.create_index(op.f("ix_work_order_assignees_tenant_id"), "work_order_assignees", ["tenant_id"], unique=False)
    op.create_index(
        "ix_work_order_assignees_tenant_order",
        "work_order_assignees",
        ["tenant_id", "order_id"],
        unique=False,
    )
    op.create_index(
        "ix_work_order_assignees_tenant_user",
        "work_order_assignees",
        ["tenant_id", "user_id"],
        unique=False,
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT tenant_id, id AS order_id, assigned_user_id AS user_id, created_at
            FROM orders
            WHERE assigned_user_id IS NOT NULL
            """
        )
    ).mappings().all()
    if rows:
        table = sa.table(
            "work_order_assignees",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
            sa.column("order_id", postgresql.UUID(as_uuid=True)),
            sa.column("user_id", postgresql.UUID(as_uuid=True)),
            sa.column("created_at", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(
            table,
            [
                {
                    "id": uuid4(),
                    "tenant_id": row["tenant_id"],
                    "order_id": row["order_id"],
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_work_order_assignees_tenant_user", table_name="work_order_assignees")
    op.drop_index("ix_work_order_assignees_tenant_order", table_name="work_order_assignees")
    op.drop_index(op.f("ix_work_order_assignees_tenant_id"), table_name="work_order_assignees")
    op.drop_table("work_order_assignees")

"""employee_full_name

Revision ID: 20260329_000007
Revises: 20260326_000006
Create Date: 2026-03-29 00:00:07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_000007"
down_revision = "20260326_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=160), nullable=True))
    op.create_index("ix_users_full_name", "users", ["full_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_full_name", table_name="users")
    op.drop_column("users", "full_name")


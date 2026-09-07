"""dashboard_preferences

Revision ID: 20260411_000010
Revises: 20260405_000009
Create Date: 2026-04-11 00:00:10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260411_000010"
down_revision = "20260405_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_preferences",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="operations"),
        sa.Column("filters_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("layout_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("baseline_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_dashboard_preferences_tenant_user"),
    )
    op.create_index(
        "ix_dashboard_preferences_tenant_user",
        "dashboard_preferences",
        ["tenant_id", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_dashboard_preferences_tenant_updated",
        "dashboard_preferences",
        ["tenant_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_preferences_tenant_updated", table_name="dashboard_preferences")
    op.drop_index("ix_dashboard_preferences_tenant_user", table_name="dashboard_preferences")
    op.drop_table("dashboard_preferences")

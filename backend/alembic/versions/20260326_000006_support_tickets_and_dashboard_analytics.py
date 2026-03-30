"""support_tickets_and_dashboard_analytics

Revision ID: 20260326_000006
Revises: 20260324_000005
Create Date: 2026-03-26 00:00:06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260326_000006"
down_revision = "20260324_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_tenant_id", "support_tickets", ["tenant_id"], unique=False)
    op.create_index("ix_support_tickets_tenant_created", "support_tickets", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_support_tickets_tenant_status", "support_tickets", ["tenant_id", "status"], unique=False)
    op.create_index("ix_support_tickets_tenant_reporter", "support_tickets", ["tenant_id", "reporter_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_support_tickets_tenant_reporter", table_name="support_tickets")
    op.drop_index("ix_support_tickets_tenant_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_tenant_created", table_name="support_tickets")
    op.drop_index("ix_support_tickets_tenant_id", table_name="support_tickets")
    op.drop_table("support_tickets")

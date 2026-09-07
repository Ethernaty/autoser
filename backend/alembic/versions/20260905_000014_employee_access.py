"""Separate service membership access from the global identity."""

from alembic import op
import sqlalchemy as sa


revision = "20260905_000014"
down_revision = "20260905_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memberships", sa.Column("job_title", sa.String(120), nullable=True))
    op.add_column("memberships", sa.Column("display_name", sa.String(160), nullable=True))
    op.add_column("memberships", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("memberships", sa.Column("can_accept_payments", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE memberships SET is_active = users.is_active, display_name = users.full_name FROM users WHERE memberships.user_id = users.id")


def downgrade() -> None:
    for name in ("can_accept_payments", "is_active", "display_name", "job_title"):
        op.drop_column("memberships", name)

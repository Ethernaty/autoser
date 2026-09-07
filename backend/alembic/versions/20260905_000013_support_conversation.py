"""Add conversation messages to support tickets."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260905_000013"
down_revision = "20260905_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("support_tickets", "messages")

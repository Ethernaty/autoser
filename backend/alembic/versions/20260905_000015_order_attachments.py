"""Add intake photo attachments to work orders."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260905_000015"
down_revision = "20260905_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    op.drop_column("orders", "attachments")

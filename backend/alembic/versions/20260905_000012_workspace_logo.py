"""Persist the workspace logo."""

from alembic import op
import sqlalchemy as sa


revision = "20260905_000012"
down_revision = "20260905_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_settings", sa.Column("logo_data_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace_settings", "logo_data_url")

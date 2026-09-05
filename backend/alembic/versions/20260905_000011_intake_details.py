"""Persist intake details without changing existing work orders."""
from alembic import op
import sqlalchemy as sa

revision = "20260905_000011"
down_revision = "20260411_000010"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("orders", sa.Column("mileage", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("estimated_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("orders", sa.Column("diagnosis", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("intake_notes", sa.Text(), nullable=True))
    op.create_check_constraint("ck_orders_mileage_nonnegative", "orders", "mileage IS NULL OR mileage >= 0")
    op.create_check_constraint("ck_orders_estimate_nonnegative", "orders", "estimated_amount IS NULL OR estimated_amount >= 0")
    op.create_index("ix_orders_tenant_due", "orders", ["tenant_id", "due_at"])

def downgrade():
    op.drop_index("ix_orders_tenant_due", table_name="orders")
    op.drop_constraint("ck_orders_estimate_nonnegative", "orders", type_="check")
    op.drop_constraint("ck_orders_mileage_nonnegative", "orders", type_="check")
    for column in ("intake_notes", "diagnosis", "estimated_amount", "due_at", "mileage"):
        op.drop_column("orders", column)

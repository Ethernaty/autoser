"""mvp_domain_alignment

Revision ID: 20260313_000004
Revises: 20260220_000003
Create Date: 2026-03-13 00:00:04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260313_000004"
down_revision = "20260220_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'membership_role') THEN
                BEGIN
                    ALTER TYPE membership_role ADD VALUE IF NOT EXISTS 'MANAGER';
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END;
            END IF;
        END
        $$;
        """
    )

    op.create_table(
        "vehicles",
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_number", sa.String(length=20), nullable=False),
        sa.Column("make_model", sa.String(length=120), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "plate_number", name="uq_vehicles_tenant_plate"),
    )
    op.create_index(op.f("ix_vehicles_tenant_id"), "vehicles", ["tenant_id"], unique=False)
    op.create_index("ix_vehicles_tenant_client", "vehicles", ["tenant_id", "client_id"], unique=False)
    op.create_index("ix_vehicles_tenant_vin", "vehicles", ["tenant_id", "vin"], unique=False)

    op.alter_column(
        "orders",
        "price",
        new_column_name="total_amount",
        existing_type=sa.Numeric(precision=12, scale=2),
        nullable=False,
    )
    op.add_column("orders", sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("orders", sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_vehicle_id_vehicles",
        "orders",
        "vehicles",
        ["vehicle_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_orders_assigned_user_id_users",
        "orders",
        "users",
        ["assigned_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_tenant_vehicle", "orders", ["tenant_id", "vehicle_id"], unique=False)
    op.create_index("ix_orders_tenant_assigned_user", "orders", ["tenant_id", "assigned_user_id"], unique=False)

    line_type_enum = sa.Enum(
        "labor",
        "part",
        "misc",
        name="order_line_type",
        native_enum=False,
    )
    line_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "order_lines",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_type", line_type_enum, nullable=False, server_default=sa.text("'labor'")),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_lines_tenant_id"), "order_lines", ["tenant_id"], unique=False)
    op.create_index("ix_order_lines_tenant_order", "order_lines", ["tenant_id", "order_id"], unique=False)
    op.create_index("ix_order_lines_tenant_line_type", "order_lines", ["tenant_id", "line_type"], unique=False)

    payment_method_enum = sa.Enum(
        "cash",
        "card",
        "transfer",
        "other",
        name="payment_method",
        native_enum=False,
    )
    payment_method_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("method", payment_method_enum, nullable=False, server_default=sa.text("'cash'")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"], unique=False)
    op.create_index("ix_payments_tenant_order", "payments", ["tenant_id", "order_id"], unique=False)
    op.create_index("ix_payments_tenant_paid_at", "payments", ["tenant_id", "paid_at"], unique=False)
    op.create_index("ix_payments_tenant_voided", "payments", ["tenant_id", "voided_at"], unique=False)

    op.create_table(
        "workspace_settings",
        sa.Column("service_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("working_hours_note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_workspace_settings_tenant"),
    )
    op.create_index(op.f("ix_workspace_settings_tenant_id"), "workspace_settings", ["tenant_id"], unique=False)
    op.create_index(
        "ix_workspace_settings_tenant_updated",
        "workspace_settings",
        ["tenant_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_settings_tenant_updated", table_name="workspace_settings")
    op.drop_index(op.f("ix_workspace_settings_tenant_id"), table_name="workspace_settings")
    op.drop_table("workspace_settings")

    op.drop_index("ix_payments_tenant_voided", table_name="payments")
    op.drop_index("ix_payments_tenant_paid_at", table_name="payments")
    op.drop_index("ix_payments_tenant_order", table_name="payments")
    op.drop_index(op.f("ix_payments_tenant_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_order_lines_tenant_line_type", table_name="order_lines")
    op.drop_index("ix_order_lines_tenant_order", table_name="order_lines")
    op.drop_index(op.f("ix_order_lines_tenant_id"), table_name="order_lines")
    op.drop_table("order_lines")

    op.drop_index("ix_orders_tenant_assigned_user", table_name="orders")
    op.drop_index("ix_orders_tenant_vehicle", table_name="orders")
    op.drop_constraint("fk_orders_assigned_user_id_users", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_vehicle_id_vehicles", "orders", type_="foreignkey")
    op.drop_column("orders", "assigned_user_id")
    op.drop_column("orders", "vehicle_id")
    op.alter_column(
        "orders",
        "total_amount",
        new_column_name="price",
        existing_type=sa.Numeric(precision=12, scale=2),
        nullable=False,
    )

    op.drop_index("ix_vehicles_tenant_vin", table_name="vehicles")
    op.drop_index("ix_vehicles_tenant_client", table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_tenant_id"), table_name="vehicles")
    op.drop_table("vehicles")

    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS order_line_type")

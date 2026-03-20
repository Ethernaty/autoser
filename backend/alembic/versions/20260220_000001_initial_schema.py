"""initial_schema

Revision ID: 20260220_000001
Revises: 
Create Date: 2026-02-20 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260220_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_clients_tenant_phone"),
    )
    op.create_index(op.f("ix_clients_tenant_id"), "clients", ["tenant_id"], unique=False)
    op.create_index("ix_clients_tenant_name", "clients", ["tenant_id", "name"], unique=False)
    op.create_index("ix_clients_tenant_phone", "clients", ["tenant_id", "phone"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "actor_id", "route", "key", name="uq_idempotency_scope_key"),
    )
    op.create_index(op.f("ix_idempotency_keys_tenant_id"), "idempotency_keys", ["tenant_id"], unique=False)
    op.create_index("ix_idempotency_expires_at", "idempotency_keys", ["expires_at"], unique=False)
    op.create_index("ix_idempotency_scope", "idempotency_keys", ["tenant_id", "actor_id", "route"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("OWNER", "ADMIN", "EMPLOYEE", name="membership_role", native_enum=False), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )
    op.create_index("ix_membership_tenant_id", "memberships", ["tenant_id"], unique=False)
    op.create_index("ix_membership_user_id", "memberships", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_audit_logs_created_at_desc", "audit_logs", [sa.text("created_at DESC")], unique=False)
    op.create_index("ix_audit_logs_entity_entity_id", "audit_logs", ["entity", "entity_id"], unique=False)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.Enum("NEW", "IN_PROGRESS", "COMPLETED", "CANCELED", name="order_status", native_enum=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_tenant_id"), "orders", ["tenant_id"], unique=False)
    op.create_index("ix_orders_tenant_client", "orders", ["tenant_id", "client_id"], unique=False)
    op.create_index("ix_orders_tenant_created_at", "orders", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_orders_tenant_status", "orders", ["tenant_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_tenant_status", table_name="orders")
    op.drop_index("ix_orders_tenant_created_at", table_name="orders")
    op.drop_index("ix_orders_tenant_client", table_name="orders")
    op.drop_index(op.f("ix_orders_tenant_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at_desc", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_membership_user_id", table_name="memberships")
    op.drop_index("ix_membership_tenant_id", table_name="memberships")
    op.drop_table("memberships")

    op.drop_index("ix_idempotency_scope", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_expires_at", table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_tenant_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index("ix_clients_tenant_phone", table_name="clients")
    op.drop_index("ix_clients_tenant_name", table_name="clients")
    op.drop_index(op.f("ix_clients_tenant_id"), table_name="clients")
    op.drop_table("clients")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS membership_role")
    op.execute("DROP TYPE IF EXISTS order_status")

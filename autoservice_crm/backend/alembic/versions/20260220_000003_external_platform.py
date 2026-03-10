"""external_platform

Revision ID: 20260220_000003
Revises: 20260220_000002
Create Date: 2026-02-20 00:00:03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260220_000003"
down_revision = "20260220_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=24), nullable=False),
        sa.Column("hashed_key", sa.String(length=128), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_api_keys_tenant_name"),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"], unique=False)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=False)
    op.create_index("ix_api_keys_tenant_revoked", "api_keys", ["tenant_id", "revoked_at"], unique=False)
    op.create_index("ix_api_keys_tenant_expires", "api_keys", ["tenant_id", "expires_at"], unique=False)

    op.create_table(
        "webhook_endpoints",
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_endpoints_tenant_id", "webhook_endpoints", ["tenant_id"], unique=False)
    op.create_index("ix_webhook_endpoints_tenant_active", "webhook_endpoints", ["tenant_id", "is_active"], unique=False)
    op.create_index("ix_webhook_endpoints_tenant_created", "webhook_endpoints", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "webhook_events",
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_events_tenant_id", "webhook_events", ["tenant_id"], unique=False)
    op.create_index("ix_webhook_events_tenant_name", "webhook_events", ["tenant_id", "event_name"], unique=False)
    op.create_index("ix_webhook_events_tenant_created", "webhook_events", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "webhook_deliveries",
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["endpoint_id"], ["webhook_endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["webhook_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_deliveries_tenant_id", "webhook_deliveries", ["tenant_id"], unique=False)
    op.create_index("ix_webhook_deliveries_tenant_status", "webhook_deliveries", ["tenant_id", "status"], unique=False)
    op.create_index("ix_webhook_deliveries_tenant_retry", "webhook_deliveries", ["tenant_id", "next_retry_at"], unique=False)
    op.create_index("ix_webhook_deliveries_endpoint_event", "webhook_deliveries", ["endpoint_id", "event_id"], unique=False)

    op.create_table(
        "integration_credentials",
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("credentials", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", "name", name="uq_integration_credentials_scope"),
    )
    op.create_index("ix_integration_credentials_tenant_id", "integration_credentials", ["tenant_id"], unique=False)
    op.create_index(
        "ix_integration_credentials_tenant_provider",
        "integration_credentials",
        ["tenant_id", "provider"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_integration_credentials_tenant_provider", table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_tenant_id", table_name="integration_credentials")
    op.drop_table("integration_credentials")

    op.drop_index("ix_webhook_deliveries_endpoint_event", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_retry", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("ix_webhook_events_tenant_created", table_name="webhook_events")
    op.drop_index("ix_webhook_events_tenant_name", table_name="webhook_events")
    op.drop_index("ix_webhook_events_tenant_id", table_name="webhook_events")
    op.drop_table("webhook_events")

    op.drop_index("ix_webhook_endpoints_tenant_created", table_name="webhook_endpoints")
    op.drop_index("ix_webhook_endpoints_tenant_active", table_name="webhook_endpoints")
    op.drop_index("ix_webhook_endpoints_tenant_id", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")

    op.drop_index("ix_api_keys_tenant_expires", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_revoked", table_name="api_keys")
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_table("api_keys")

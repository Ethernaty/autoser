"""monetization_governance

Revision ID: 20260220_000002
Revises: 20260220_000001
Create Date: 2026-02-20 00:00:02
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260220_000002"
down_revision = "20260220_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tenant_state_enum = sa.Enum(
        "active",
        "suspended",
        "disabled",
        "deleted",
        name="tenant_state",
        native_enum=False,
    )
    subscription_status_enum = sa.Enum(
        "active",
        "trial",
        "past_due",
        "canceled",
        "suspended",
        name="subscription_status",
        native_enum=False,
    )
    tenant_state_enum.create(op.get_bind(), checkfirst=True)
    subscription_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "tenants",
        sa.Column(
            "state",
            tenant_state_enum,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "plans",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_name"), "plans", ["name"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", subscription_status_enum, nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_subscriptions_tenant_id"),
    )
    op.create_index(op.f("ix_subscriptions_tenant_id"), "subscriptions", ["tenant_id"], unique=False)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)

    op.create_table(
        "tenant_feature_overrides",
        sa.Column("feature_name", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "feature_name", name="uq_tenant_feature_override"),
    )
    op.create_index(op.f("ix_tenant_feature_overrides_tenant_id"), "tenant_feature_overrides", ["tenant_id"], unique=False)
    op.create_index(
        "ix_tenant_feature_overrides_feature_name",
        "tenant_feature_overrides",
        ["feature_name"],
        unique=False,
    )

    op.create_table(
        "usage_counters",
        sa.Column("resource", sa.String(length=80), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("soft_warning_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "resource", "period_start", name="uq_usage_tenant_resource_period"),
    )
    op.create_index(op.f("ix_usage_counters_tenant_id"), "usage_counters", ["tenant_id"], unique=False)
    op.create_index("ix_usage_counters_resource_period", "usage_counters", ["resource", "period_start"], unique=False)

    op.create_table(
        "billing_events",
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_billing_events_tenant_id"), "billing_events", ["tenant_id"], unique=False)
    op.create_index("ix_billing_events_tenant_created_at", "billing_events", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_billing_events_type", "billing_events", ["type"], unique=False)

    starter_plan_id = str(uuid.uuid4())
    growth_plan_id = str(uuid.uuid4())
    enterprise_plan_id = str(uuid.uuid4())

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO plans (id, name, price, limits, features, is_active, description, created_at)
            VALUES
                (:starter_id, 'starter', 0, '{"clients": 1000, "orders": 3000}', '{"orders": true, "clients": true, "analytics": false}', true, 'Starter plan', now()),
                (:growth_id, 'growth', 49, '{"clients": 5000, "orders": 20000}', '{"orders": true, "clients": true, "analytics": true, "advanced_reports": true}', true, 'Growth plan', now()),
                (:enterprise_id, 'enterprise', 199, '{"clients": 50000, "orders": 200000}', '{"orders": true, "clients": true, "analytics": true, "advanced_reports": true, "api_access": true}', true, 'Enterprise plan', now())
            ON CONFLICT (name) DO NOTHING
            """
        ),
        {
            "starter_id": starter_plan_id,
            "growth_id": growth_plan_id,
            "enterprise_id": enterprise_plan_id,
        },
    )

    starter_plan_id_row = bind.execute(sa.text("SELECT id FROM plans WHERE name = 'starter' LIMIT 1")).fetchone()
    if starter_plan_id_row:
        starter_plan_uuid = starter_plan_id_row[0]
        tenants_without_subscription = bind.execute(
            sa.text(
                """
                SELECT t.id
                FROM tenants t
                WHERE NOT EXISTS (
                    SELECT 1 FROM subscriptions s WHERE s.tenant_id = t.id
                )
                """
            )
        ).fetchall()

        now = datetime.now(UTC)
        subscriptions_rows: list[dict[str, object]] = []
        billing_rows: list[dict[str, object]] = []
        for row in tenants_without_subscription:
            tenant_id = row[0]
            subscription_id = uuid.uuid4()
            subscriptions_rows.append(
                {
                    "id": subscription_id,
                    "tenant_id": tenant_id,
                    "plan_id": starter_plan_uuid,
                    "status": "trial",
                    "current_period_start": now,
                    "current_period_end": now + timedelta(days=30),
                    "cancel_at_period_end": False,
                    "trial_end": now + timedelta(days=14),
                    "created_at": now,
                    "updated_at": now,
                }
            )
            billing_rows.append(
                {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_id,
                    "type": "subscription.bootstrap",
                    "payload": {"plan_id": str(starter_plan_uuid), "status": "trial"},
                    "created_at": now,
                }
            )

        if subscriptions_rows:
            subscriptions_table = sa.table(
                "subscriptions",
                sa.column("id", postgresql.UUID(as_uuid=True)),
                sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
                sa.column("plan_id", postgresql.UUID(as_uuid=True)),
                sa.column("status", sa.String),
                sa.column("current_period_start", sa.DateTime(timezone=True)),
                sa.column("current_period_end", sa.DateTime(timezone=True)),
                sa.column("cancel_at_period_end", sa.Boolean),
                sa.column("trial_end", sa.DateTime(timezone=True)),
                sa.column("created_at", sa.DateTime(timezone=True)),
                sa.column("updated_at", sa.DateTime(timezone=True)),
            )
            op.bulk_insert(subscriptions_table, subscriptions_rows)

        if billing_rows:
            billing_table = sa.table(
                "billing_events",
                sa.column("id", postgresql.UUID(as_uuid=True)),
                sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
                sa.column("type", sa.String),
                sa.column("payload", postgresql.JSONB(astext_type=sa.Text())),
                sa.column("created_at", sa.DateTime(timezone=True)),
            )
            op.bulk_insert(billing_table, billing_rows)


def downgrade() -> None:
    op.drop_index("ix_billing_events_type", table_name="billing_events")
    op.drop_index("ix_billing_events_tenant_created_at", table_name="billing_events")
    op.drop_index(op.f("ix_billing_events_tenant_id"), table_name="billing_events")
    op.drop_table("billing_events")

    op.drop_index("ix_usage_counters_resource_period", table_name="usage_counters")
    op.drop_index(op.f("ix_usage_counters_tenant_id"), table_name="usage_counters")
    op.drop_table("usage_counters")

    op.drop_index("ix_tenant_feature_overrides_feature_name", table_name="tenant_feature_overrides")
    op.drop_index(op.f("ix_tenant_feature_overrides_tenant_id"), table_name="tenant_feature_overrides")
    op.drop_table("tenant_feature_overrides")

    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_tenant_id"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_plans_name"), table_name="plans")
    op.drop_table("plans")

    op.drop_column("tenants", "updated_at")
    op.drop_column("tenants", "state")

    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS tenant_state")


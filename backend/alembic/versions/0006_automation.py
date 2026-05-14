"""Phase 6 automation: policy, durable job queue, incidents."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_automation"
down_revision: str | Sequence[str] | None = "0005_premium_entitlements_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_policies",
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kill_switch_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_amount_rao_per_action", sa.BigInteger(), nullable=False, server_default="1000000000"),
        sa.Column("max_daily_jobs", sa.Integer(), nullable=False, server_default="48"),
        sa.Column(
            "allowed_validator_hotkeys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allowed_subnet_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("compound_threshold_rao", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("wallet_address"),
    )

    op.create_table(
        "automation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_jobs_wallet_status", "automation_jobs", ["wallet_address", "status"])
    op.create_index("ix_automation_jobs_status_scheduled", "automation_jobs", ["status", "scheduled_for"])

    op.create_table(
        "automation_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["automation_jobs.id"], name="fk_automation_incidents_job", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_incidents_wallet", "automation_incidents", ["wallet_address"])


def downgrade() -> None:
    op.drop_index("ix_automation_incidents_wallet", table_name="automation_incidents")
    op.drop_table("automation_incidents")
    op.drop_index("ix_automation_jobs_status_scheduled", table_name="automation_jobs")
    op.drop_index("ix_automation_jobs_wallet_status", table_name="automation_jobs")
    op.drop_table("automation_jobs")
    op.drop_table("automation_policies")

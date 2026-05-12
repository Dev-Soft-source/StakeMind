"""Phase 1 schema draft."""

# ruff: noqa: E501
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_phase1"
down_revision: str | Sequence[str] | None = "0001_phase0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subnets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "validators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hotkey", sa.String(length=128), nullable=False),
        sa.Column("coldkey", sa.String(length=128), nullable=True),
        sa.Column("subnet_id", sa.BigInteger(), nullable=False),
        sa.Column("uid", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_seen_block", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hotkey", "subnet_id", name="uq_validators_hotkey_subnet"),
    )
    op.create_index("ix_validators_hotkey", "validators", ["hotkey"])
    op.create_index("ix_validators_subnet_id", "validators", ["subnet_id"])
    op.create_table(
        "stakes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("validator_hotkey", sa.String(length=128), nullable=False),
        sa.Column("subnet_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_rao", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_seen_block", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "wallet_address",
            "validator_hotkey",
            "subnet_id",
            name="uq_stakes_wallet_validator_subnet",
        ),
    )
    op.create_index("ix_stakes_wallet_address", "stakes", ["wallet_address"])
    op.create_index("ix_stakes_validator_hotkey", "stakes", ["validator_hotkey"])
    op.create_index("ix_stakes_subnet_id", "stakes", ["subnet_id"])
    op.create_table(
        "reward_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("subnet_id", sa.BigInteger(), nullable=False),
        sa.Column("validator_hotkey", sa.String(length=128), nullable=True),
        sa.Column("amount_rao", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reward_snapshots_wallet_address", "reward_snapshots", ["wallet_address"])
    op.create_index("ix_reward_snapshots_subnet_id", "reward_snapshots", ["subnet_id"])
    op.create_index("ix_reward_snapshots_validator_hotkey", "reward_snapshots", ["validator_hotkey"])
    op.create_index("ix_reward_snapshots_block_number", "reward_snapshots", ["block_number"])
    op.create_table(
        "wallet_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wallet_sessions_wallet_address", "wallet_sessions", ["wallet_address"])
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_wallet", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_actor_wallet", "audit_events", ["actor_wallet"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("chain_head", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_ingestion_runs_job_name", "ingestion_runs", ["job_name"])


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("audit_events")
    op.drop_table("wallet_sessions")
    op.drop_table("reward_snapshots")
    op.drop_table("stakes")
    op.drop_table("validators")
    op.drop_table("subnets")

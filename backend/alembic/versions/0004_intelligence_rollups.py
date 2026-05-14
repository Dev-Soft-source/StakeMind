"""Phase 4 intelligence rollups."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_intelligence_rollups"
down_revision: str | Sequence[str] | None = "0003_staking_transactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "validator_score_rollups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hotkey", sa.String(length=128), nullable=False),
        sa.Column("subnet_id", sa.BigInteger(), nullable=False),
        sa.Column("as_of_block", sa.BigInteger(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("composite_score", sa.Integer(), nullable=False),
        sa.Column("apy_estimate", sa.Float(), nullable=False),
        sa.Column("reward_consistency", sa.Float(), nullable=False),
        sa.Column("uptime_percent", sa.Float(), nullable=False),
        sa.Column("rank_subnet", sa.Integer(), nullable=False),
        sa.Column("rank_global", sa.Integer(), nullable=False),
        sa.Column("delegation_trend", sa.Float(), nullable=False),
        sa.Column("reputation_signal", sa.Float(), nullable=False),
        sa.Column("inputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("methodology_version", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["validator_id"], ["validators.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("validator_id", name="uq_validator_score_rollups_validator_id"),
    )
    op.create_index(
        "ix_validator_score_rollups_subnet_score",
        "validator_score_rollups",
        ["subnet_id", "composite_score"],
    )
    op.create_index(
        "ix_validator_score_rollups_subnet_rank",
        "validator_score_rollups",
        ["subnet_id", "rank_subnet"],
    )
    op.create_table(
        "wallet_risk_rollups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("as_of_block", sa.BigInteger(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("concentration_validator", sa.Float(), nullable=False),
        sa.Column("concentration_subnet", sa.Float(), nullable=False),
        sa.Column("hhi_validator", sa.Float(), nullable=False),
        sa.Column("hhi_subnet", sa.Float(), nullable=False),
        sa.Column("reward_volatility", sa.Float(), nullable=False),
        sa.Column("downtime_risk_proxy", sa.Float(), nullable=False),
        sa.Column("overall_risk_band", sa.String(length=16), nullable=False),
        sa.Column("inputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("methodology_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wallet_address", name="uq_wallet_risk_rollups_wallet_address"),
    )
    op.create_index("ix_wallet_risk_rollups_wallet_address", "wallet_risk_rollups", ["wallet_address"])


def downgrade() -> None:
    op.drop_table("wallet_risk_rollups")
    op.drop_table("validator_score_rollups")

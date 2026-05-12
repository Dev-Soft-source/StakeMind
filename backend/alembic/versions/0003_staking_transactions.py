"""Phase 3 staking transaction tracking."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_staking_transactions"
down_revision: str | Sequence[str] | None = "0002_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staking_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("subnet_id", sa.BigInteger(), nullable=False),
        sa.Column("source_validator_hotkey", sa.String(length=128), nullable=True),
        sa.Column("dest_validator_hotkey", sa.String(length=128), nullable=True),
        sa.Column("amount_rao", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("unsigned_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("simulation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("signed_extrinsic", sa.Text(), nullable=True),
        sa.Column("tx_hash", sa.String(length=128), nullable=True),
        sa.Column("block_hash", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "wallet_address",
            "idempotency_key",
            name="uq_staking_transactions_wallet_idempotency",
        ),
    )
    op.create_index("ix_staking_transactions_wallet_address", "staking_transactions", ["wallet_address"])
    op.create_index("ix_staking_transactions_status", "staking_transactions", ["status"])
    op.create_index("ix_staking_transactions_tx_hash", "staking_transactions", ["tx_hash"])


def downgrade() -> None:
    op.drop_table("staking_transactions")

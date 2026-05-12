from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Subnet(Base, TimestampMixin):
    __tablename__ = "subnets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    validators: Mapped[list["Validator"]] = relationship(back_populates="subnet")


class Validator(Base, TimestampMixin):
    __tablename__ = "validators"
    __table_args__ = (UniqueConstraint("hotkey", "subnet_id", name="uq_validators_hotkey_subnet"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    hotkey: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    coldkey: Mapped[str | None] = mapped_column(String(128))
    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"), nullable=False, index=True)
    uid: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    last_seen_block: Mapped[int | None] = mapped_column(BigInteger)

    subnet: Mapped["Subnet"] = relationship(back_populates="validators")


class Stake(Base, TimestampMixin):
    __tablename__ = "stakes"
    __table_args__ = (
        UniqueConstraint(
            "wallet_address",
            "validator_hotkey",
            "subnet_id",
            name="uq_stakes_wallet_validator_subnet",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    validator_hotkey: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"), nullable=False, index=True)
    amount_rao: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_seen_block: Mapped[int | None] = mapped_column(BigInteger)


class RewardSnapshot(Base):
    __tablename__ = "reward_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"), nullable=False, index=True)
    validator_hotkey: Mapped[str | None] = mapped_column(String(128), index=True)
    amount_rao: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WalletSession(Base):
    __tablename__ = "wallet_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_wallet: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    chain_head: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StakingTransaction(Base, TimestampMixin):
    __tablename__ = "staking_transactions"
    __table_args__ = (
        UniqueConstraint(
            "wallet_address",
            "idempotency_key",
            name="uq_staking_transactions_wallet_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    subnet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_validator_hotkey: Mapped[str | None] = mapped_column(String(128))
    dest_validator_hotkey: Mapped[str | None] = mapped_column(String(128))
    amount_rao: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    unsigned_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    simulation_result: Mapped[dict | None] = mapped_column(JSONB)
    signed_extrinsic: Mapped[str | None] = mapped_column(Text)
    tx_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    block_hash: Mapped[str | None] = mapped_column(String(128))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

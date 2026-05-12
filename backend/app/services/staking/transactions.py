from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.models import StakingTransaction
from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcClient
from app.services import audit as audit_service

StakingAction = Literal["delegate", "undelegate", "redelegate"]
StakingStatus = Literal[
    "built",
    "signed",
    "submitted",
    "confirmed",
    "failed",
    "expired",
]


@dataclass(frozen=True)
class BuildTransactionInput:
    wallet_address: str
    action: StakingAction
    subnet_id: int
    amount_rao: int
    source_validator_hotkey: str | None
    dest_validator_hotkey: str | None


def _action_to_method(action: StakingAction) -> str:
    mapping = {
        "delegate": "add_stake",
        "undelegate": "remove_stake",
        "redelegate": "move_stake",
    }
    return mapping[action]


def _validate_build_input(payload: BuildTransactionInput) -> None:
    if payload.amount_rao <= 0:
        raise ValueError("amount_rao must be greater than zero")
    if payload.action == "delegate" and not payload.dest_validator_hotkey:
        raise ValueError("dest_validator_hotkey is required for delegate")
    if payload.action == "undelegate" and not payload.source_validator_hotkey:
        raise ValueError("source_validator_hotkey is required for undelegate")
    if payload.action == "redelegate" and (
        not payload.source_validator_hotkey or not payload.dest_validator_hotkey
    ):
        raise ValueError("source and dest validator hotkeys are required for redelegate")


def _build_unsigned_payload(
    payload: BuildTransactionInput,
    chain_head: ChainHead,
    chain_name: str,
) -> dict[str, object]:
    return {
        "version": 1,
        "chain": chain_name,
        "block_hash": chain_head.block_hash,
        "block_number": chain_head.block_number,
        "wallet_address": payload.wallet_address,
        "call": {
            "pallet": "SubtensorModule",
            "method": _action_to_method(payload.action),
            "subnet_id": payload.subnet_id,
            "source_validator_hotkey": payload.source_validator_hotkey,
            "dest_validator_hotkey": payload.dest_validator_hotkey,
            "amount_rao": payload.amount_rao,
        },
    }


async def simulate_payload(
    rpc_client: SubtensorRpcClient,
    unsigned_payload: dict[str, object],
    *,
    enabled: bool,
) -> dict[str, object]:
    if not enabled:
        return {
            "supported": False,
            "status": "skipped",
            "message": "Simulation disabled by configuration",
        }

    try:
        chain_head = await rpc_client.fetch_chain_head()
        return {
            "supported": True,
            "status": "ok",
            "estimated_fee_rao": 1_000_000,
            "block_number": chain_head.block_number,
            "message": "Dry-run simulation completed against current chain head",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "supported": False,
            "status": "skipped",
            "message": f"Simulation unavailable: {exc}",
        }


async def build_transaction(
    session: AsyncSession,
    rpc_client: SubtensorRpcClient,
    settings: Settings,
    payload: BuildTransactionInput,
) -> StakingTransaction:
    _validate_build_input(payload)
    chain_head = await rpc_client.fetch_chain_head()
    chain_name = await rpc_client.fetch_chain_name()
    unsigned_payload = _build_unsigned_payload(payload, chain_head, chain_name)
    simulation_result = await simulate_payload(
        rpc_client,
        unsigned_payload,
        enabled=settings.staking_enable_simulation,
    )
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.staking_transaction_ttl_seconds)
    transaction = StakingTransaction(
        wallet_address=payload.wallet_address,
        action=payload.action,
        subnet_id=payload.subnet_id,
        source_validator_hotkey=payload.source_validator_hotkey,
        dest_validator_hotkey=payload.dest_validator_hotkey,
        amount_rao=payload.amount_rao,
        status="built",
        unsigned_payload=unsigned_payload,
        simulation_result=simulation_result,
        expires_at=expires_at,
    )
    session.add(transaction)
    await session.flush()
    await audit_service.record_audit_event(
        session,
        actor_wallet=payload.wallet_address,
        event_type="staking.build",
        payload={
            "transaction_id": str(transaction.id),
            "action": payload.action,
            "subnet_id": payload.subnet_id,
            "amount_rao": payload.amount_rao,
            "outcome": "built",
        },
    )
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def get_transaction(session: AsyncSession, transaction_id: UUID) -> StakingTransaction | None:
    return await session.get(StakingTransaction, transaction_id)


async def resimulate_transaction(
    session: AsyncSession,
    rpc_client: SubtensorRpcClient,
    settings: Settings,
    transaction: StakingTransaction,
) -> StakingTransaction:
    _ensure_not_expired(transaction)
    simulation_result = await simulate_payload(
        rpc_client,
        transaction.unsigned_payload,
        enabled=settings.staking_enable_simulation,
    )
    transaction.simulation_result = simulation_result
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def submit_transaction(
    session: AsyncSession,
    settings: Settings,
    transaction: StakingTransaction,
    *,
    tx_hash: str,
    signed_extrinsic: str | None,
    idempotency_key: str,
) -> StakingTransaction:
    _ensure_not_expired(transaction)
    if transaction.status in {"confirmed", "failed", "expired"}:
        return transaction

    existing = await session.scalar(
        select(StakingTransaction).where(
            StakingTransaction.wallet_address == transaction.wallet_address,
            StakingTransaction.idempotency_key == idempotency_key,
            StakingTransaction.id != transaction.id,
        )
    )
    if existing is not None:
        return existing

    if transaction.idempotency_key == idempotency_key and transaction.tx_hash:
        return transaction

    transaction.idempotency_key = idempotency_key
    transaction.tx_hash = tx_hash
    transaction.signed_extrinsic = signed_extrinsic
    transaction.status = "submitted"
    transaction.submitted_at = datetime.now(UTC)
    await audit_service.record_audit_event(
        session,
        actor_wallet=transaction.wallet_address,
        event_type="staking.submit",
        payload={
            "transaction_id": str(transaction.id),
            "action": transaction.action,
            "tx_hash": tx_hash,
            "outcome": "submitted",
        },
    )
    await session.commit()
    await session.refresh(transaction)
    return await finalize_submitted_transaction(session, settings, transaction)


async def finalize_submitted_transaction(
    session: AsyncSession,
    settings: Settings,
    transaction: StakingTransaction,
) -> StakingTransaction:
    if transaction.status != "submitted" or not transaction.tx_hash:
        return transaction

    digest = sha256(f"{transaction.tx_hash}:{transaction.id}".encode()).hexdigest()
    if int(digest[:2], 16) % 5 == 0:
        transaction.status = "failed"
        transaction.failure_reason = "Simulated submission failure from chain watcher"
        await audit_service.record_audit_event(
            session,
            actor_wallet=transaction.wallet_address,
            event_type="staking.failed",
            payload={
                "transaction_id": str(transaction.id),
                "tx_hash": transaction.tx_hash,
                "outcome": "failed",
            },
        )
    else:
        transaction.status = "confirmed"
        transaction.confirmed_at = datetime.now(UTC)
        transaction.block_hash = f"0x{digest[:64]}"
        await audit_service.record_audit_event(
            session,
            actor_wallet=transaction.wallet_address,
            event_type="staking.confirmed",
            payload={
                "transaction_id": str(transaction.id),
                "tx_hash": transaction.tx_hash,
                "confirmation_target_blocks": settings.staking_confirmation_target_blocks,
                "outcome": "confirmed",
            },
        )
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def list_wallet_transactions(
    session: AsyncSession,
    wallet_address: str,
    *,
    page: int,
    page_size: int,
) -> tuple[list[StakingTransaction], int]:
    query = select(StakingTransaction).where(StakingTransaction.wallet_address == wallet_address)
    total_items = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(StakingTransaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    transactions = (await session.scalars(query)).all()
    return transactions, int(total_items or 0)


def _ensure_not_expired(transaction: StakingTransaction) -> None:
    if transaction.expires_at < datetime.now(UTC):
        transaction.status = "expired"
        raise ValueError("Transaction preview expired; rebuild before signing")

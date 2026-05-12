from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RewardSnapshot, Stake, Subnet, Validator
from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcClient


@dataclass(frozen=True)
class CatalogSyncResult:
    chain_head: int
    validators_upserted: int
    subnets_processed: int


def _build_validator_metadata(subnet_id: int, index: int) -> dict[str, object]:
    seed = sha256(f"{subnet_id}:{index}".encode()).hexdigest()
    score = 70 + int(seed[:2], 16) % 26
    apy = round(8 + int(seed[2:4], 16) / 255 * 12, 2)
    uptime = round(94 + int(seed[4:6], 16) / 255 * 5, 2)
    return {
        "display_name": f"Validator {subnet_id}-{index + 1}",
        "reliability_score": score,
        "apy_estimate": apy,
        "uptime_percent": uptime,
        "reward_consistency": round(0.75 + int(seed[6:8], 16) / 255 * 0.2, 2),
        "delegated_stake_rao": 1_000_000_000 + int(seed[8:16], 16),
    }


async def sync_validator_catalog(
    session: AsyncSession,
    chain_head: ChainHead,
    validators_per_subnet: int = 8,
) -> CatalogSyncResult:
    subnet_ids = (await session.scalars(select(Subnet.id).order_by(Subnet.id))).all()
    upserted = 0
    for subnet_id in subnet_ids:
        for index in range(validators_per_subnet):
            hotkey = (
                f"5StakeMind{subnet_id:03d}{index:02d}"
                f"{sha256(f'{subnet_id}:{index}'.encode()).hexdigest()[:40]}"
            )
            existing = await session.scalar(
                select(Validator).where(
                    Validator.hotkey == hotkey,
                    Validator.subnet_id == subnet_id,
                )
            )
            metadata = _build_validator_metadata(subnet_id, index)
            if existing is None:
                session.add(
                    Validator(
                        hotkey=hotkey,
                        subnet_id=subnet_id,
                        uid=index,
                        is_active=True,
                        metadata_json=metadata,
                        last_seen_block=chain_head.block_number,
                    )
                )
                upserted += 1
            else:
                existing.metadata_json = metadata
                existing.last_seen_block = chain_head.block_number
                existing.is_active = True
    await session.commit()
    return CatalogSyncResult(
        chain_head=chain_head.block_number,
        validators_upserted=upserted,
        subnets_processed=len(subnet_ids),
    )


@dataclass(frozen=True)
class PortfolioSyncResult:
    wallet_address: str
    chain_head: int
    stakes_upserted: int
    reward_points_written: int


async def sync_wallet_portfolio(
    session: AsyncSession,
    wallet_address: str,
    chain_head: ChainHead,
    history_days: int = 30,
) -> PortfolioSyncResult:
    validators = (
        await session.scalars(
            select(Validator).where(Validator.is_active.is_(True)).order_by(Validator.subnet_id)
        )
    ).all()
    selected = validators[: min(6, len(validators))]
    stakes_upserted = 0
    for index, validator in enumerate(selected):
        amount_rao = 500_000_000 + index * 125_000_000
        existing = await session.scalar(
            select(Stake).where(
                Stake.wallet_address == wallet_address,
                Stake.validator_hotkey == validator.hotkey,
                Stake.subnet_id == validator.subnet_id,
            )
        )
        if existing is None:
            session.add(
                Stake(
                    wallet_address=wallet_address,
                    validator_hotkey=validator.hotkey,
                    subnet_id=validator.subnet_id,
                    amount_rao=amount_rao,
                    last_seen_block=chain_head.block_number,
                )
            )
            stakes_upserted += 1
        else:
            existing.amount_rao = amount_rao
            existing.last_seen_block = chain_head.block_number

    reward_points_written = 0
    now = datetime.now(UTC)
    for day_offset in range(history_days):
        captured_at = now - timedelta(days=history_days - day_offset)
        block_number = max(chain_head.block_number - day_offset * 100, 1)
        for index, validator in enumerate(selected[:3]):
            amount_rao = 1_000_000 + day_offset * 50_000 + index * 10_000
            session.add(
                RewardSnapshot(
                    wallet_address=wallet_address,
                    subnet_id=validator.subnet_id,
                    validator_hotkey=validator.hotkey,
                    amount_rao=amount_rao,
                    block_number=block_number,
                    captured_at=captured_at,
                )
            )
            reward_points_written += 1
    await session.commit()
    return PortfolioSyncResult(
        wallet_address=wallet_address,
        chain_head=chain_head.block_number,
        stakes_upserted=stakes_upserted,
        reward_points_written=reward_points_written,
    )


async def fetch_chain_head(client: SubtensorRpcClient) -> ChainHead:
    return await client.fetch_chain_head()

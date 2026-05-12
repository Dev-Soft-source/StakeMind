from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RewardSnapshot, Stake, Validator


def _validator_sort_column(sort: str):
    mapping = {
        "score": Validator.metadata_json["reliability_score"].as_integer(),
        "apy": Validator.metadata_json["apy_estimate"].as_float(),
        "hotkey": Validator.hotkey,
    }
    return mapping.get(sort, Validator.metadata_json["reliability_score"].as_integer())


async def list_validators(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    subnet_id: int | None,
    search: str | None,
    sort: str,
    direction: str,
) -> tuple[list[Validator], int]:
    query: Select[tuple[Validator]] = select(Validator).where(Validator.is_active.is_(True))
    if subnet_id is not None:
        query = query.where(Validator.subnet_id == subnet_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Validator.hotkey.ilike(pattern),
                Validator.metadata_json["display_name"].as_string().ilike(pattern),
            )
        )

    total_items = await session.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = _validator_sort_column(sort)
    query = query.order_by(sort_column.desc() if direction == "desc" else sort_column.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    validators = (await session.scalars(query)).all()
    return validators, int(total_items or 0)


async def get_validator(
    session: AsyncSession,
    *,
    hotkey: str,
    subnet_id: int | None,
) -> Validator | None:
    query = select(Validator).where(Validator.hotkey == hotkey, Validator.is_active.is_(True))
    if subnet_id is not None:
        query = query.where(Validator.subnet_id == subnet_id)
    return await session.scalar(query)


async def list_stakes_for_wallet(session: AsyncSession, wallet_address: str) -> list[Stake]:
    return (
        await session.scalars(
            select(Stake)
            .where(Stake.wallet_address == wallet_address)
            .order_by(Stake.subnet_id, Stake.validator_hotkey)
        )
    ).all()


async def reward_summary(session: AsyncSession, wallet_address: str) -> dict[str, int]:
    total_rewards = await session.scalar(
        select(func.coalesce(func.sum(RewardSnapshot.amount_rao), 0)).where(
            RewardSnapshot.wallet_address == wallet_address
        )
    )
    total_stake = await session.scalar(
        select(func.coalesce(func.sum(Stake.amount_rao), 0)).where(
            Stake.wallet_address == wallet_address
        )
    )
    return {
        "total_rewards_rao": int(total_rewards or 0),
        "total_stake_rao": int(total_stake or 0),
    }


async def reward_history(
    session: AsyncSession,
    wallet_address: str,
    *,
    days: int,
) -> list[RewardSnapshot]:
    return (
        await session.scalars(
            select(RewardSnapshot)
            .where(RewardSnapshot.wallet_address == wallet_address)
            .order_by(RewardSnapshot.captured_at.asc())
            .limit(days * 10)
        )
    ).all()

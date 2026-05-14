from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    RewardSnapshot,
    Stake,
    ValidatorScoreRollup,
    WalletRiskRollup,
)
from app.services.intelligence.scoring import (
    LIMITATIONS,
    METHODOLOGY_VERSION,
    forecast_daily_rewards,
    implied_apy_percent,
)


async def list_rankings(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    subnet_id: int | None,
    sort: str,
    direction: str,
) -> tuple[list[ValidatorScoreRollup], int]:
    query: Select[tuple[ValidatorScoreRollup]] = select(ValidatorScoreRollup)
    if subnet_id is not None:
        query = query.where(ValidatorScoreRollup.subnet_id == subnet_id)
    total_items = await session.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = {
        "score": ValidatorScoreRollup.composite_score,
        "apy": ValidatorScoreRollup.apy_estimate,
        "rank": ValidatorScoreRollup.rank_subnet,
    }.get(sort, ValidatorScoreRollup.composite_score)
    query = query.order_by(sort_column.desc() if direction == "desc" else sort_column.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.scalars(query)).all()
    return rows, int(total_items or 0)


async def get_validator_intelligence(
    session: AsyncSession,
    *,
    hotkey: str,
    subnet_id: int | None,
) -> ValidatorScoreRollup | None:
    query = select(ValidatorScoreRollup).where(ValidatorScoreRollup.hotkey == hotkey)
    if subnet_id is not None:
        query = query.where(ValidatorScoreRollup.subnet_id == subnet_id)
    return await session.scalar(query)


async def compare_validators(
    session: AsyncSession,
    *,
    hotkeys: list[str],
    subnet_id: int | None,
) -> list[ValidatorScoreRollup]:
    query = select(ValidatorScoreRollup).where(ValidatorScoreRollup.hotkey.in_(hotkeys))
    if subnet_id is not None:
        query = query.where(ValidatorScoreRollup.subnet_id == subnet_id)
    return (await session.scalars(query)).all()


async def get_wallet_risk(session: AsyncSession, wallet_address: str) -> WalletRiskRollup | None:
    return await session.scalar(
        select(WalletRiskRollup).where(WalletRiskRollup.wallet_address == wallet_address)
    )


async def build_reward_forecast(
    session: AsyncSession,
    *,
    wallet_address: str,
    days: int,
    horizon_days: int,
) -> dict[str, object]:
    reward_rows = (
        await session.scalars(
            select(RewardSnapshot)
            .where(RewardSnapshot.wallet_address == wallet_address)
            .order_by(RewardSnapshot.captured_at.asc())
            .limit(days * 10)
        )
    ).all()
    daily_totals: dict[str, int] = {}
    for point in reward_rows:
        day = point.captured_at.date().isoformat()
        daily_totals[day] = daily_totals.get(day, 0) + point.amount_rao
    ordered_days = list(daily_totals.values())
    forecasts = forecast_daily_rewards(ordered_days, horizon_days)
    total_stake = await session.scalar(
        select(func.coalesce(func.sum(Stake.amount_rao), 0)).where(
            Stake.wallet_address == wallet_address
        )
    )
    mean_daily = sum(ordered_days) / len(ordered_days) if ordered_days else 0.0
    return {
        "wallet_address": wallet_address,
        "methodology_version": METHODOLOGY_VERSION,
        "limitations": LIMITATIONS,
        "is_estimate": True,
        "implied_apy_pct": implied_apy_percent(mean_daily, int(total_stake or 0)),
        "history_days": len(ordered_days),
        "forecast": [
            {"day_offset": index + 1, "amount_rao": amount}
            for index, amount in enumerate(forecasts)
        ],
    }

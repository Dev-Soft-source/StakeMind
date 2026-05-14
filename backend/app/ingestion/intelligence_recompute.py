from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    IngestionRun,
    RewardSnapshot,
    Stake,
    Validator,
    ValidatorScoreRollup,
    WalletRiskRollup,
)
from app.integrations.bittensor.rpc import ChainHead
from app.services.intelligence.scoring import (
    METHODOLOGY_VERSION,
    ValidatorScoreInputs,
    WalletRiskInputs,
    compute_validator_score,
    compute_wallet_risk,
)


@dataclass(frozen=True)
class IntelligenceRecomputeResult:
    chain_head: int
    validators_scored: int
    wallets_scored: int
    reused_existing: bool


async def recompute_intelligence(
    session: AsyncSession,
    chain_head: ChainHead,
    *,
    window_days: int = 30,
) -> IntelligenceRecomputeResult:
    idempotency_key = f"intelligence:{chain_head.block_hash}:{window_days}"
    existing = await session.scalar(
        select(IngestionRun).where(IngestionRun.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return IntelligenceRecomputeResult(
            chain_head=chain_head.block_number,
            validators_scored=0,
            wallets_scored=0,
            reused_existing=True,
        )

    validators = (
        await session.scalars(select(Validator).where(Validator.is_active.is_(True)))
    ).all()
    stakes_by_subnet: dict[int, list[int]] = {}
    for validator in validators:
        delegated = int(validator.metadata_json.get("delegated_stake_rao", 0))
        stakes_by_subnet.setdefault(validator.subnet_id, []).append(delegated)

    score_rows: list[ValidatorScoreRollup] = []
    for validator in validators:
        pool_median = int(median(stakes_by_subnet.get(validator.subnet_id, [0])))
        delegated = int(validator.metadata_json.get("delegated_stake_rao", 0))
        result = compute_validator_score(
            ValidatorScoreInputs(
                uptime_percent=float(validator.metadata_json.get("uptime_percent", 0.0)),
                reward_consistency=float(validator.metadata_json.get("reward_consistency", 0.0)),
                apy_estimate=float(validator.metadata_json.get("apy_estimate", 0.0)),
                delegated_stake_rao=delegated,
                pool_median_stake_rao=max(pool_median, 1),
            )
        )
        existing_row = await session.scalar(
            select(ValidatorScoreRollup).where(ValidatorScoreRollup.validator_id == validator.id)
        )
        row = existing_row or ValidatorScoreRollup(validator_id=validator.id)
        row.hotkey = validator.hotkey
        row.subnet_id = validator.subnet_id
        row.as_of_block = chain_head.block_number
        row.computed_at = datetime.now(UTC)
        row.composite_score = result.composite_score
        row.apy_estimate = float(validator.metadata_json.get("apy_estimate", 0.0))
        row.reward_consistency = float(validator.metadata_json.get("reward_consistency", 0.0))
        row.uptime_percent = float(validator.metadata_json.get("uptime_percent", 0.0))
        row.delegation_trend = result.delegation_trend
        row.reputation_signal = result.reputation_signal
        row.inputs_json = result.inputs
        row.methodology_version = METHODOLOGY_VERSION
        if existing_row is None:
            session.add(row)
        score_rows.append(row)

    await session.flush()
    score_rows.sort(key=lambda item: item.composite_score, reverse=True)
    for index, row in enumerate(score_rows, start=1):
        row.rank_global = index
    for subnet_id in {row.subnet_id for row in score_rows}:
        subnet_rows = sorted(
            [row for row in score_rows if row.subnet_id == subnet_id],
            key=lambda item: item.composite_score,
            reverse=True,
        )
        for index, row in enumerate(subnet_rows, start=1):
            row.rank_subnet = index

    wallet_addresses = (
        await session.scalars(select(Stake.wallet_address).distinct())
    ).all()
    wallets_scored = 0
    for wallet_address in wallet_addresses:
        stakes = (
            await session.scalars(select(Stake).where(Stake.wallet_address == wallet_address))
        ).all()
        total_stake = sum(stake.amount_rao for stake in stakes)
        if total_stake <= 0:
            continue
        validator_weights = {
            stake.validator_hotkey: stake.amount_rao / total_stake for stake in stakes
        }
        subnet_totals: dict[str, int] = {}
        for stake in stakes:
            subnet_totals[str(stake.subnet_id)] = (
                subnet_totals.get(str(stake.subnet_id), 0) + stake.amount_rao
            )
        subnet_weights = {
            subnet: amount / total_stake for subnet, amount in subnet_totals.items()
        }
        reward_rows = (
            await session.scalars(
                select(RewardSnapshot)
                .where(RewardSnapshot.wallet_address == wallet_address)
                .order_by(RewardSnapshot.captured_at.asc())
                .limit(window_days * 10)
            )
        ).all()
        daily_totals: dict[str, int] = {}
        for point in reward_rows:
            day = point.captured_at.date().isoformat()
            daily_totals[day] = daily_totals.get(day, 0) + point.amount_rao
        downtime_weighted = 0.0
        for stake in stakes:
            rollup = await session.scalar(
                select(ValidatorScoreRollup).where(
                    ValidatorScoreRollup.hotkey == stake.validator_hotkey,
                    ValidatorScoreRollup.subnet_id == stake.subnet_id,
                )
            )
            uptime = rollup.uptime_percent if rollup else 0.0
            downtime_weighted += (100.0 - uptime) * (stake.amount_rao / total_stake)
        risk = compute_wallet_risk(
            WalletRiskInputs(
                validator_weights=validator_weights,
                subnet_weights=subnet_weights,
                daily_reward_totals=list(daily_totals.values()),
                downtime_proxy_percent=downtime_weighted,
            )
        )
        existing_risk = await session.scalar(
            select(WalletRiskRollup).where(WalletRiskRollup.wallet_address == wallet_address)
        )
        risk_row = existing_risk or WalletRiskRollup(wallet_address=wallet_address)
        risk_row.as_of_block = chain_head.block_number
        risk_row.computed_at = datetime.now(UTC)
        risk_row.concentration_validator = risk.concentration_validator
        risk_row.concentration_subnet = risk.concentration_subnet
        risk_row.hhi_validator = risk.hhi_validator
        risk_row.hhi_subnet = risk.hhi_subnet
        risk_row.reward_volatility = risk.reward_volatility
        risk_row.downtime_risk_proxy = risk.downtime_risk_proxy
        risk_row.overall_risk_band = risk.overall_risk_band
        risk_row.inputs_json = risk.inputs
        risk_row.methodology_version = METHODOLOGY_VERSION
        if existing_risk is None:
            session.add(risk_row)
        wallets_scored += 1

    session.add(
        IngestionRun(
            job_name="intelligence_recompute",
            idempotency_key=idempotency_key,
            chain_head=chain_head.block_number,
            status="succeeded",
            detail=f"validators={len(score_rows)} wallets={wallets_scored}",
        )
    )
    await session.commit()
    return IntelligenceRecomputeResult(
        chain_head=chain_head.block_number,
        validators_scored=len(score_rows),
        wallets_scored=wallets_scored,
        reused_existing=False,
    )

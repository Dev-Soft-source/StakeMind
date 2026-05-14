"""Job handlers: scans and incidents only — never signs or submits chain transactions."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AutomationIncident,
    AutomationJob,
    AutomationPolicy,
    StakingTransaction,
)
from app.services import portfolio as portfolio_service
from app.services.intelligence.queries import get_wallet_risk


async def _add_incident(
    session: AsyncSession,
    *,
    wallet_address: str,
    job_id,
    severity: str,
    code: str,
    message: str,
    meta: dict | None = None,
) -> AutomationIncident:
    row = AutomationIncident(
        id=uuid4(),
        wallet_address=wallet_address,
        job_id=job_id,
        severity=severity,
        code=code,
        message=message,
        meta=meta or {},
    )
    session.add(row)
    await session.flush()
    return row


async def _incident_exists_for_meta(
    session: AsyncSession,
    *,
    wallet_address: str,
    code: str,
    meta_key: str,
    meta_value: str,
) -> bool:
    fragment = {meta_key: meta_value}
    q = select(AutomationIncident.id).where(
        AutomationIncident.wallet_address == wallet_address,
        AutomationIncident.code == code,
        AutomationIncident.meta.contains(fragment),
        AutomationIncident.resolved_at.is_(None),
    )
    return await session.scalar(q) is not None


async def run_compound_opportunity_scan(
    session: AsyncSession,
    job: AutomationJob,
    policy: AutomationPolicy,
) -> None:
    summary = await portfolio_service.reward_summary(session, job.wallet_address)
    total = int(summary.get("total_rewards_rao", 0))
    threshold = int(policy.compound_threshold_rao)
    if threshold > 0 and total >= threshold:
        await _add_incident(
            session,
            wallet_address=job.wallet_address,
            job_id=job.id,
            severity="info",
            code="compound_opportunity",
            message=(
                f"Reward balance {total} rao meets your automation threshold. "
                "Review and sign any stake action manually — StakeMind never submits transactions."
            ),
            meta={"total_rewards_rao": total, "threshold_rao": threshold},
        )


async def run_rebalance_scan(session: AsyncSession, job: AutomationJob) -> None:
    risk = await get_wallet_risk(session, job.wallet_address)
    if risk is None:
        return
    if float(risk.concentration_validator) > 0.55:
        await _add_incident(
            session,
            wallet_address=job.wallet_address,
            job_id=job.id,
            severity="warning",
            code="rebalance_candidate",
            message=(
                "Validator concentration is elevated in the latest risk rollup. "
                "Consider manual redelegation within your policy; automation does not execute moves."
            ),
            meta={"concentration_validator": float(risk.concentration_validator)},
        )


async def run_stuck_transaction_scan(session: AsyncSession, job: AutomationJob) -> None:
    now = datetime.now(UTC)
    cutoff_submit = now - timedelta(minutes=15)
    cutoff_built = now - timedelta(hours=1)
    txs = (
        await session.scalars(
            select(StakingTransaction)
            .where(StakingTransaction.wallet_address == job.wallet_address)
            .where(
                or_(
                    and_(
                        StakingTransaction.status == "submitted",
                        StakingTransaction.submitted_at.is_not(None),
                        StakingTransaction.submitted_at < cutoff_submit,
                    ),
                    and_(StakingTransaction.status == "built", StakingTransaction.created_at < cutoff_built),
                )
            )
        )
    ).all()
    for tx in txs:
        tx_key = str(tx.id)
        if await _incident_exists_for_meta(
            session,
            wallet_address=job.wallet_address,
            code="stuck_transaction",
            meta_key="staking_transaction_id",
            meta_value=tx_key,
        ):
            continue
        await _add_incident(
            session,
            wallet_address=job.wallet_address,
            job_id=job.id,
            severity="warning",
            code="stuck_transaction",
            message=(
                f"Transaction {tx.id} is in status '{tx.status}' longer than expected. "
                "Check wallet/RPC or rebuild if expired. No automatic submission is performed."
            ),
            meta={"staking_transaction_id": tx_key, "status": tx.status},
        )


async def run_schedule_tick(_session: AsyncSession, _job: AutomationJob) -> None:
    """Reserved for recurring schedules; does not perform on-chain actions."""
    pass

async def dispatch_job(
    session: AsyncSession,
    job: AutomationJob,
    policy: AutomationPolicy,
) -> None:
    if job.job_type == "compound_opportunity_scan":
        await run_compound_opportunity_scan(session, job, policy)
    elif job.job_type == "rebalance_scan":
        await run_rebalance_scan(session, job)
    elif job.job_type == "stuck_transaction_scan":
        await run_stuck_transaction_scan(session, job)
    elif job.job_type == "schedule_tick":
        await run_schedule_tick(session, job)
    else:
        raise ValueError("unknown_job_type")

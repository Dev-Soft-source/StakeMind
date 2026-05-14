"""Automation policy: opt-in, kill switch, caps, allowlists (server-side only)."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AutomationJob, AutomationPolicy

ALLOWED_JOB_TYPES = frozenset(
    {
        "compound_opportunity_scan",
        "rebalance_scan",
        "stuck_transaction_scan",
        "schedule_tick",
    }
)


async def get_or_create_policy(session: AsyncSession, wallet_address: str) -> AutomationPolicy:
    row = await session.get(AutomationPolicy, wallet_address)
    if row is not None:
        return row
    row = AutomationPolicy(
        wallet_address=wallet_address,
        opt_in=False,
        kill_switch_active=False,
        max_amount_rao_per_action=1_000_000_000,
        max_daily_jobs=48,
        allowed_validator_hotkeys=[],
        allowed_subnet_ids=[],
        compound_threshold_rao=0,
    )
    session.add(row)
    await session.flush()
    return row


async def count_jobs_since_midnight_utc(session: AsyncSession, wallet_address: str) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count = await session.scalar(
        select(func.count())
        .select_from(AutomationJob)
        .where(
            AutomationJob.wallet_address == wallet_address,
            AutomationJob.created_at >= start,
            AutomationJob.status != "cancelled",
        )
    )
    return int(count or 0)


def assert_payload_within_policy(policy: AutomationPolicy, payload: dict) -> None:
    amount = payload.get("amount_rao")
    if amount is not None and int(amount) > int(policy.max_amount_rao_per_action):
        raise ValueError("amount_exceeds_policy_cap")

    hotkey = payload.get("validator_hotkey") or payload.get("dest_validator_hotkey")
    allow_v = policy.allowed_validator_hotkeys or []
    if allow_v and hotkey and hotkey not in allow_v:
        raise ValueError("validator_not_allowlisted")

    subnet = payload.get("subnet_id")
    allow_s = policy.allowed_subnet_ids or []
    if allow_s and subnet is not None and int(subnet) not in [int(x) for x in allow_s]:
        raise ValueError("subnet_not_allowlisted")


async def assert_may_enqueue(
    session: AsyncSession,
    policy: AutomationPolicy,
    *,
    job_type: str,
    payload: dict,
) -> None:
    if job_type not in ALLOWED_JOB_TYPES:
        raise ValueError("unknown_job_type")
    if not policy.opt_in:
        raise ValueError("automation_not_opted_in")
    if policy.kill_switch_active:
        raise ValueError("kill_switch_active")
    assert_payload_within_policy(policy, payload)
    daily = await count_jobs_since_midnight_utc(session, policy.wallet_address)
    if daily >= int(policy.max_daily_jobs):
        raise ValueError("daily_job_cap_reached")

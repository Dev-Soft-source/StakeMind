"""PostgreSQL-backed automation job queue (durable; worker is a separate process)."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AutomationIncident, AutomationJob
from app.services.automation import policy as policy_service


async def enqueue_job(
    session: AsyncSession,
    *,
    wallet_address: str,
    job_type: str,
    payload: dict,
    scheduled_for: datetime | None = None,
) -> AutomationJob:
    pol = await policy_service.get_or_create_policy(session, wallet_address)
    await policy_service.assert_may_enqueue(session, pol, job_type=job_type, payload=payload)
    when = scheduled_for or datetime.now(UTC)
    job = AutomationJob(
        id=uuid4(),
        wallet_address=wallet_address,
        job_type=job_type,
        payload=payload,
        status="pending",
        scheduled_for=when,
    )
    session.add(job)
    await session.flush()
    return job


async def claim_next_pending_job(session: AsyncSession) -> AutomationJob | None:
    now = datetime.now(UTC)
    job = await session.scalar(
        select(AutomationJob)
        .where(
            AutomationJob.status == "pending",
            AutomationJob.scheduled_for <= now,
        )
        .order_by(AutomationJob.scheduled_for)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = "running"
    job.started_at = now
    job.attempts = int(job.attempts) + 1
    await session.flush()
    return job


async def mark_job_completed(session: AsyncSession, job: AutomationJob) -> None:
    job.status = "completed"
    job.finished_at = datetime.now(UTC)
    job.error_message = None
    await session.flush()


async def mark_job_failed(session: AsyncSession, job: AutomationJob, message: str) -> None:
    if job.attempts >= job.max_attempts:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
    else:
        job.status = "pending"
        job.scheduled_for = datetime.now(UTC)
    job.error_message = message[:4000]
    await session.flush()


async def mark_job_cancelled(session: AsyncSession, job: AutomationJob, reason: str) -> None:
    job.status = "cancelled"
    job.finished_at = datetime.now(UTC)
    job.error_message = reason[:4000]
    await session.flush()


async def list_wallet_jobs(
    session: AsyncSession,
    wallet_address: str,
    *,
    status: str | None,
    limit: int = 50,
) -> list[AutomationJob]:
    q = select(AutomationJob).where(AutomationJob.wallet_address == wallet_address)
    if status:
        q = q.where(AutomationJob.status == status)
    q = q.order_by(AutomationJob.created_at.desc()).limit(limit)
    return (await session.scalars(q)).all()


async def list_wallet_incidents(
    session: AsyncSession,
    wallet_address: str,
    *,
    limit: int = 50,
) -> list[AutomationIncident]:
    return (
        await session.scalars(
            select(AutomationIncident)
            .where(AutomationIncident.wallet_address == wallet_address)
            .order_by(AutomationIncident.created_at.desc())
            .limit(limit)
        )
    ).all()

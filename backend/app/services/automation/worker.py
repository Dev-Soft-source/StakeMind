"""Worker entrypoints for automation jobs (run as a separate process, not in-request)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.automation import policy as policy_service
from app.services.automation.handlers import dispatch_job
from app.services.automation.queue import (
    claim_next_pending_job,
    mark_job_cancelled,
    mark_job_completed,
    mark_job_failed,
)


async def process_next_job(session: AsyncSession) -> bool:
    job = await claim_next_pending_job(session)
    if job is None:
        return False
    policy = await policy_service.get_or_create_policy(session, job.wallet_address)
    if not policy.opt_in or policy.kill_switch_active:
        await mark_job_cancelled(session, job, "policy_blocked_mid_queue")
        return True
    try:
        await dispatch_job(session, job, policy)
        await mark_job_completed(session, job)
    except Exception as exc:
        await mark_job_failed(session, job, str(exc))
    return True

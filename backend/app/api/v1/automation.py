from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import assert_wallet_scope
from app.api.v1.schemas.automation import (
    AUTOMATION_LEGAL_COPY,
    AutomationIncidentResponse,
    AutomationJobEnqueue,
    AutomationJobResponse,
    AutomationPolicyResponse,
    AutomationPolicyUpdate,
    KillSwitchRequest,
)
from app.database.models import AutomationPolicy
from app.database.session import get_db_session
from app.services import audit as audit_service
from app.services.automation import policy as policy_service
from app.services.automation.queue import enqueue_job, list_wallet_incidents, list_wallet_jobs

router = APIRouter(tags=["automation"])


def _to_policy_response(row: AutomationPolicy) -> AutomationPolicyResponse:
    return AutomationPolicyResponse(
        wallet_address=row.wallet_address,
        opt_in=bool(row.opt_in),
        kill_switch_active=bool(row.kill_switch_active),
        max_amount_rao_per_action=int(row.max_amount_rao_per_action),
        max_daily_jobs=int(row.max_daily_jobs),
        allowed_validator_hotkeys=list(row.allowed_validator_hotkeys or []),
        allowed_subnet_ids=[int(x) for x in (row.allowed_subnet_ids or [])],
        compound_threshold_rao=int(row.compound_threshold_rao),
    )


def _to_job_response(job) -> AutomationJobResponse:
    return AutomationJobResponse(
        id=job.id,
        wallet_address=job.wallet_address,
        job_type=job.job_type,
        payload=dict(job.payload or {}),
        status=job.status,
        scheduled_for=job.scheduled_for,
        attempts=int(job.attempts),
        max_attempts=int(job.max_attempts),
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _to_incident_response(row) -> AutomationIncidentResponse:
    return AutomationIncidentResponse(
        id=row.id,
        wallet_address=row.wallet_address,
        job_id=row.job_id,
        severity=row.severity,
        code=row.code,
        message=row.message,
        meta=dict(row.meta or {}),
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


@router.get("/wallets/{wallet_address}/automation/policy", response_model=AutomationPolicyResponse)
async def get_automation_policy(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> AutomationPolicyResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    row = await policy_service.get_or_create_policy(session, wallet_address)
    await session.commit()
    await session.refresh(row)
    return _to_policy_response(row)


@router.put("/wallets/{wallet_address}/automation/policy", response_model=AutomationPolicyResponse)
async def put_automation_policy(
    wallet_address: str,
    body: AutomationPolicyUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> AutomationPolicyResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    row = await policy_service.get_or_create_policy(session, wallet_address)
    if body.opt_in is not None:
        row.opt_in = body.opt_in
    if body.kill_switch_active is not None:
        row.kill_switch_active = body.kill_switch_active
    if body.max_amount_rao_per_action is not None:
        row.max_amount_rao_per_action = body.max_amount_rao_per_action
    if body.max_daily_jobs is not None:
        row.max_daily_jobs = body.max_daily_jobs
    if body.allowed_validator_hotkeys is not None:
        row.allowed_validator_hotkeys = body.allowed_validator_hotkeys
    if body.allowed_subnet_ids is not None:
        row.allowed_subnet_ids = body.allowed_subnet_ids
    if body.compound_threshold_rao is not None:
        row.compound_threshold_rao = body.compound_threshold_rao
    session.add(row)
    await audit_service.record_audit_event(
        session,
        actor_wallet=wallet_address,
        event_type="automation.policy_update",
        payload={"opt_in": row.opt_in, "kill_switch_active": row.kill_switch_active},
    )
    await session.commit()
    await session.refresh(row)
    return _to_policy_response(row)


@router.post("/wallets/{wallet_address}/automation/kill-switch", response_model=AutomationPolicyResponse)
async def post_kill_switch(
    wallet_address: str,
    body: KillSwitchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> AutomationPolicyResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    row = await policy_service.get_or_create_policy(session, wallet_address)
    row.kill_switch_active = bool(body.active)
    session.add(row)
    await audit_service.record_audit_event(
        session,
        actor_wallet=wallet_address,
        event_type="automation.kill_switch",
        payload={"active": body.active},
    )
    await session.commit()
    await session.refresh(row)
    return _to_policy_response(row)


@router.post("/wallets/{wallet_address}/automation/jobs", response_model=AutomationJobResponse)
async def post_automation_job(
    wallet_address: str,
    body: AutomationJobEnqueue,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> AutomationJobResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    if body.scheduled_for is not None:
        latest = datetime.now(UTC) + timedelta(days=30)
        if body.scheduled_for > latest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduled_for too far in the future",
            )
    try:
        job = await enqueue_job(
            session,
            wallet_address=wallet_address,
            job_type=body.job_type,
            payload=body.payload,
            scheduled_for=body.scheduled_for,
        )
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "automation_not_opted_in": status.HTTP_403_FORBIDDEN,
            "kill_switch_active": status.HTTP_403_FORBIDDEN,
            "daily_job_cap_reached": status.HTTP_429_TOO_MANY_REQUESTS,
            "unknown_job_type": status.HTTP_400_BAD_REQUEST,
        }
        st = mapping.get(code, status.HTTP_400_BAD_REQUEST)
        raise HTTPException(status_code=st, detail=code) from exc

    await audit_service.record_audit_event(
        session,
        actor_wallet=wallet_address,
        event_type="automation.job_enqueued",
        payload={"job_id": str(job.id), "job_type": job.job_type},
    )
    await session.commit()
    await session.refresh(job)
    return _to_job_response(job)


@router.get("/wallets/{wallet_address}/automation/jobs", response_model=list[AutomationJobResponse])
async def get_automation_jobs(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[AutomationJobResponse]:
    assert_wallet_scope(wallet_address, x_wallet_address)
    jobs = await list_wallet_jobs(session, wallet_address, status=status_filter, limit=50)
    return [_to_job_response(j) for j in jobs]


@router.get("/wallets/{wallet_address}/automation/incidents", response_model=list[AutomationIncidentResponse])
async def get_automation_incidents(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> list[AutomationIncidentResponse]:
    assert_wallet_scope(wallet_address, x_wallet_address)
    rows = await list_wallet_incidents(session, wallet_address, limit=50)
    return [_to_incident_response(r) for r in rows]


@router.get("/automation/legal", response_model=dict[str, str])
async def get_automation_legal() -> dict[str, str]:
    return {"disclaimer": AUTOMATION_LEGAL_COPY}

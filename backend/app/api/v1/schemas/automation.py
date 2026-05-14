from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

AUTOMATION_LEGAL_COPY = (
    "Automation jobs only enqueue scans and informational incidents. StakeMind never signs transactions "
    "or submits extrinsics on your behalf. External security review of your deployment is recommended "
    "before relying on automation in production."
)


class AutomationPolicyResponse(BaseModel):
    wallet_address: str
    opt_in: bool
    kill_switch_active: bool
    max_amount_rao_per_action: int
    max_daily_jobs: int
    allowed_validator_hotkeys: list[str]
    allowed_subnet_ids: list[int]
    compound_threshold_rao: int
    disclaimer: str = AUTOMATION_LEGAL_COPY


class AutomationPolicyUpdate(BaseModel):
    opt_in: bool | None = None
    kill_switch_active: bool | None = None
    max_amount_rao_per_action: int | None = Field(default=None, ge=1, le=10**18)
    max_daily_jobs: int | None = Field(default=None, ge=1, le=500)
    allowed_validator_hotkeys: list[str] | None = None
    allowed_subnet_ids: list[int] | None = None
    compound_threshold_rao: int | None = Field(default=None, ge=0, le=10**18)


class KillSwitchRequest(BaseModel):
    active: bool


class AutomationJobEnqueue(BaseModel):
    job_type: str = Field(
        pattern="^(compound_opportunity_scan|rebalance_scan|stuck_transaction_scan|schedule_tick)$"
    )
    payload: dict = Field(default_factory=dict)
    scheduled_for: datetime | None = None


class AutomationJobResponse(BaseModel):
    id: UUID
    wallet_address: str
    job_type: str
    payload: dict
    status: str
    scheduled_for: datetime
    attempts: int
    max_attempts: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AutomationIncidentResponse(BaseModel):
    id: UUID
    wallet_address: str
    job_id: UUID | None
    severity: str
    code: str
    message: str
    meta: dict
    created_at: datetime
    resolved_at: datetime | None

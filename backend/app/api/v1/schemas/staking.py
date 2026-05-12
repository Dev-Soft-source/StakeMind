from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BuildStakingTransactionRequest(BaseModel):
    wallet_address: str = Field(min_length=10, max_length=128)
    action: Literal["delegate", "undelegate", "redelegate"]
    subnet_id: int = Field(ge=0)
    amount_rao: int = Field(gt=0)
    source_validator_hotkey: str | None = Field(default=None, max_length=128)
    dest_validator_hotkey: str | None = Field(default=None, max_length=128)


class StakingSimulationResponse(BaseModel):
    supported: bool
    status: str
    message: str
    estimated_fee_rao: int | None = None
    block_number: int | None = None


class StakingTransactionPreview(BaseModel):
    action: str
    subnet_id: int
    amount_rao: int
    source_validator_hotkey: str | None
    dest_validator_hotkey: str | None
    estimated_fee_rao: int | None = None


class StakingTransactionResponse(BaseModel):
    id: UUID
    wallet_address: str
    action: str
    subnet_id: int
    amount_rao: int
    source_validator_hotkey: str | None
    dest_validator_hotkey: str | None
    status: str
    unsigned_payload: dict[str, object]
    simulation: StakingSimulationResponse | None
    tx_hash: str | None
    failure_reason: str | None
    expires_at: datetime
    submitted_at: datetime | None
    confirmed_at: datetime | None
    preview: StakingTransactionPreview


class SubmitStakingTransactionRequest(BaseModel):
    tx_hash: str = Field(min_length=10, max_length=128)
    signed_extrinsic: str | None = None

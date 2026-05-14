from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WalletEntitlementResponse(BaseModel):
    plan: str
    source: str | None = None
    valid_until: str | None = None


class RedeemInviteRequest(BaseModel):
    code: str = Field(min_length=4, max_length=64)


class RedeemInviteResponse(BaseModel):
    plan: str
    source: str
    message: str


class AdvancedScoreRow(BaseModel):
    hotkey: str
    subnet_id: int
    composite_score: int
    optimization_score: float
    reputation_signal: float
    apy_estimate: float


class AdvancedScoresResponse(BaseModel):
    data: list[AdvancedScoreRow]
    limitations: list[str]


class OptimizationHintsResponse(BaseModel):
    hints: list[str]
    limitations: list[str]


class SubnetExposureRow(BaseModel):
    subnet_id: int
    stake_rao: int
    share_of_wallet: float


class SubnetAnalyticsResponse(BaseModel):
    wallet_address: str
    subnets: list[SubnetExposureRow]
    limitations: list[str]


class PortfolioRecommendation(BaseModel):
    title: str
    detail: str


class RecommendationsResponse(BaseModel):
    wallet_address: str
    recommendations: list[PortfolioRecommendation]
    disclaimer: str


class PriorityRefreshResponse(BaseModel):
    invalidated_namespaces: list[str]


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    rule_type: str = Field(pattern="^risk_band_equals$")
    threshold_json: dict = Field(default_factory=dict)
    channel: str = Field(pattern="^(in_app|email|webhook)$")
    webhook_url: str | None = None
    enabled: bool = True
    quiet_hours_start_utc: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end_utc: int | None = Field(default=None, ge=0, le=23)


class AlertRuleResponse(BaseModel):
    id: UUID
    wallet_address: str
    name: str
    rule_type: str
    threshold_json: dict
    channel: str
    webhook_url: str | None
    enabled: bool
    quiet_hours_start_utc: int | None
    quiet_hours_end_utc: int | None


class AlertEvaluationItem(BaseModel):
    rule_id: UUID
    fired: bool
    skipped_reason: str | None
    channel: str


class AlertEvaluateResponse(BaseModel):
    results: list[AlertEvaluationItem]


class InAppNotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    read_at: str | None
    created_at: datetime

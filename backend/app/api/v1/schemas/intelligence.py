from datetime import datetime

from pydantic import BaseModel, Field


class IntelligenceMeta(BaseModel):
    methodology_version: str
    as_of_block: int
    computed_at: datetime
    limitations: list[str]


class ValidatorRankingResponse(BaseModel):
    hotkey: str
    subnet_id: int
    composite_score: int
    apy_estimate: float
    reward_consistency: float
    uptime_percent: float
    rank_subnet: int
    rank_global: int
    delegation_trend: float
    reputation_signal: float
    meta: IntelligenceMeta


class ValidatorIntelligenceResponse(ValidatorRankingResponse):
    inputs: dict[str, float]


class WalletRiskResponse(BaseModel):
    wallet_address: str
    concentration_validator: float
    concentration_subnet: float
    hhi_validator: float
    hhi_subnet: float
    reward_volatility: float
    downtime_risk_proxy: float
    overall_risk_band: str
    inputs: dict[str, float]
    meta: IntelligenceMeta


class ForecastPoint(BaseModel):
    day_offset: int
    amount_rao: int


class RewardForecastResponse(BaseModel):
    wallet_address: str
    methodology_version: str
    limitations: list[str]
    is_estimate: bool = True
    implied_apy_pct: float
    history_days: int
    forecast: list[ForecastPoint]


class CompareValidatorsResponse(BaseModel):
    validators: list[ValidatorIntelligenceResponse]
    limitations: list[str]

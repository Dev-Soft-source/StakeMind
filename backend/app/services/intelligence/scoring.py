from dataclasses import dataclass
from math import log1p
from statistics import mean, pstdev

METHODOLOGY_VERSION = "mvp-v1"
LIMITATIONS = [
    "Scores use stored snapshot metadata, not live chain performance feeds.",
    "Wallet reward history is synthetic in local MVP sync flows.",
    "Forecasts are estimates and are not guarantees of future rewards.",
]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class ValidatorScoreInputs:
    uptime_percent: float
    reward_consistency: float
    apy_estimate: float
    delegated_stake_rao: int
    pool_median_stake_rao: int


@dataclass(frozen=True)
class ValidatorScoreResult:
    composite_score: int
    delegation_trend: float
    reputation_signal: float
    inputs: dict[str, float]


def compute_validator_score(inputs: ValidatorScoreInputs) -> ValidatorScoreResult:
    uptime_norm = clamp(inputs.uptime_percent / 100.0, 0.0, 1.0)
    consistency = clamp(inputs.reward_consistency, 0.0, 1.0)
    apy_norm = clamp(inputs.apy_estimate / 20.0, 0.0, 1.0)
    median = max(inputs.pool_median_stake_rao, 1)
    delegation_norm = clamp(log1p(inputs.delegated_stake_rao) / log1p(median), 0.0, 1.0)
    composite = round(
        100
        * (
            0.35 * uptime_norm
            + 0.30 * consistency
            + 0.25 * apy_norm
            + 0.10 * delegation_norm
        )
    )
    delegation_trend = clamp((inputs.delegated_stake_rao - median) / median, -1.0, 1.0)
    reputation_signal = clamp(0.7 * consistency + 0.3 * uptime_norm, 0.0, 1.0)
    return ValidatorScoreResult(
        composite_score=composite,
        delegation_trend=delegation_trend,
        reputation_signal=reputation_signal,
        inputs={
            "uptime_norm": uptime_norm,
            "consistency": consistency,
            "apy_norm": apy_norm,
            "delegation_norm": delegation_norm,
        },
    )


@dataclass(frozen=True)
class WalletRiskInputs:
    validator_weights: dict[str, float]
    subnet_weights: dict[str, float]
    daily_reward_totals: list[int]
    downtime_proxy_percent: float


@dataclass(frozen=True)
class WalletRiskResult:
    concentration_validator: float
    concentration_subnet: float
    hhi_validator: float
    hhi_subnet: float
    reward_volatility: float
    downtime_risk_proxy: float
    overall_risk_band: str
    inputs: dict[str, float]


def compute_wallet_risk(inputs: WalletRiskInputs) -> WalletRiskResult:
    concentration_validator = max(inputs.validator_weights.values(), default=0.0)
    concentration_subnet = max(inputs.subnet_weights.values(), default=0.0)
    hhi_validator = sum(weight * weight for weight in inputs.validator_weights.values())
    hhi_subnet = sum(weight * weight for weight in inputs.subnet_weights.values())
    if len(inputs.daily_reward_totals) >= 2:
        reward_mean = mean(inputs.daily_reward_totals)
        reward_volatility = pstdev(inputs.daily_reward_totals) / max(reward_mean, 1.0)
    else:
        reward_volatility = 0.0
    reward_volatility = clamp(reward_volatility, 0.0, 1.0)
    downtime_risk_proxy = clamp(inputs.downtime_proxy_percent, 0.0, 100.0)
    if concentration_validator > 0.7 or reward_volatility > 0.6:
        band = "high"
    elif concentration_validator <= 0.4 and reward_volatility <= 0.35:
        band = "low"
    else:
        band = "medium"
    return WalletRiskResult(
        concentration_validator=concentration_validator,
        concentration_subnet=concentration_subnet,
        hhi_validator=hhi_validator,
        hhi_subnet=hhi_subnet,
        reward_volatility=reward_volatility,
        downtime_risk_proxy=downtime_risk_proxy,
        overall_risk_band=band,
        inputs={
            "concentration_validator": concentration_validator,
            "concentration_subnet": concentration_subnet,
            "reward_volatility": reward_volatility,
        },
    )


def forecast_daily_rewards(daily_totals: list[int], horizon_days: int) -> list[int]:
    if not daily_totals:
        return [0 for _ in range(horizon_days)]
    window = daily_totals[-min(14, len(daily_totals)) :]
    n = len(window)
    if n == 1:
        baseline = window[0]
        return [max(0, baseline) for _ in range(horizon_days)]
    x_values = list(range(n))
    x_mean = mean(x_values)
    y_mean = mean(window)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, window, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in x_values) or 1.0
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    forecasts: list[int] = []
    for horizon in range(1, horizon_days + 1):
        value = intercept + slope * (n + horizon - 1)
        forecasts.append(max(0, int(round(value))))
    return forecasts


def implied_apy_percent(mean_daily_rewards_rao: float, total_stake_rao: int) -> float:
    if total_stake_rao <= 0:
        return 0.0
    return round((mean_daily_rewards_rao * 365 / total_stake_rao) * 100, 2)

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pytest  # noqa: E402

from app.services.intelligence.scoring import (  # noqa: E402
    ValidatorScoreInputs,
    WalletRiskInputs,
    clamp,
    compute_validator_score,
    compute_wallet_risk,
    forecast_daily_rewards,
    implied_apy_percent,
)


def test_compute_validator_score_matches_documented_weights() -> None:
    result = compute_validator_score(
        ValidatorScoreInputs(
            uptime_percent=100.0,
            reward_consistency=1.0,
            apy_estimate=20.0,
            delegated_stake_rao=2_000_000_000,
            pool_median_stake_rao=1_000_000_000,
        )
    )
    assert result.composite_score == 100
    assert result.delegation_trend == 1.0
    assert result.reputation_signal == 1.0


def test_compute_wallet_risk_band_high_concentration() -> None:
    result = compute_wallet_risk(
        WalletRiskInputs(
            validator_weights={"a": 0.8, "b": 0.2},
            subnet_weights={"1": 1.0},
            daily_reward_totals=[100, 120, 80, 110],
            downtime_proxy_percent=12.0,
        )
    )
    assert result.overall_risk_band == "high"
    assert result.concentration_validator == 0.8


def test_forecast_daily_rewards_returns_horizon_length() -> None:
    forecasts = forecast_daily_rewards([100, 110, 120, 130], horizon_days=5)
    assert len(forecasts) == 5
    assert all(value >= 0 for value in forecasts)


def test_implied_apy_percent() -> None:
    assert implied_apy_percent(1_000_000, 1_000_000_000) == 36.5


def test_implied_apy_percent_zero_stake() -> None:
    assert implied_apy_percent(1_000_000, 0) == 0.0


def test_clamp_bounds() -> None:
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(99.0, 0.0, 10.0) == 10.0


def test_forecast_daily_rewards_empty_input() -> None:
    assert forecast_daily_rewards([], horizon_days=4) == [0, 0, 0, 0]


def test_forecast_daily_rewards_single_observation() -> None:
    assert forecast_daily_rewards([42], horizon_days=3) == [42, 42, 42]


def test_compute_wallet_risk_low_band() -> None:
    result = compute_wallet_risk(
        WalletRiskInputs(
            validator_weights={"a": 0.3, "b": 0.35, "c": 0.35},
            subnet_weights={"1": 0.5, "2": 0.5},
            daily_reward_totals=[100, 102, 101],
            downtime_proxy_percent=5.0,
        )
    )
    assert result.overall_risk_band == "low"


def test_compute_validator_score_with_tiny_pool_median() -> None:
    result = compute_validator_score(
        ValidatorScoreInputs(
            uptime_percent=80.0,
            reward_consistency=0.5,
            apy_estimate=10.0,
            delegated_stake_rao=100,
            pool_median_stake_rao=0,
        )
    )
    assert 0 <= result.composite_score <= 100
    assert result.delegation_trend <= 1.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

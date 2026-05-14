from app.services.intelligence.scoring import (
    ValidatorScoreInputs,
    WalletRiskInputs,
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

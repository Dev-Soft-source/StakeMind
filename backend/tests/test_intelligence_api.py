import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database.session import get_db_session  # noqa: E402


@pytest.fixture
def mock_db_session():
    async def _override():
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))
        yield session

    return _override


@pytest.mark.asyncio
async def test_validator_rankings_returns_paginated_payload(app, mock_db_session) -> None:
    rollup = type(
        "ValidatorScoreRollup",
        (),
        {
            "hotkey": "5Hotkey",
            "subnet_id": 1,
            "composite_score": 88,
            "apy_estimate": 12.0,
            "reward_consistency": 0.9,
            "uptime_percent": 98.0,
            "rank_subnet": 1,
            "rank_global": 2,
            "delegation_trend": 0.1,
            "reputation_signal": 0.92,
            "methodology_version": "mvp-v1",
            "as_of_block": 42,
            "computed_at": "2026-01-01T00:00:00+00:00",
        },
    )()

    with patch(
        "app.api.v1.intelligence.list_rankings",
        new_callable=AsyncMock,
        return_value=([rollup], 1),
    ):
        app.dependency_overrides[get_db_session] = mock_db_session
        try:
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/api/v1/intelligence/validators/rankings")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total_items"] == 1
    assert payload["data"][0]["composite_score"] == 88


@pytest.mark.asyncio
async def test_wallet_risk_requires_wallet_scope(app, mock_db_session) -> None:
    wallet = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
    other = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
    app.dependency_overrides[get_db_session] = mock_db_session
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/wallets/{wallet}/risk",
                    headers={"X-Wallet-Address": other},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reward_forecast_is_labeled_estimate(app, mock_db_session) -> None:
    with patch(
        "app.api.v1.intelligence.build_reward_forecast",
        new_callable=AsyncMock,
        return_value={
            "wallet_address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "methodology_version": "mvp-v1",
            "limitations": ["Forecasts are estimates and are not guarantees of future rewards."],
            "is_estimate": True,
            "implied_apy_pct": 4.2,
            "history_days": 7,
            "forecast": [{"day_offset": 1, "amount_rao": 1000}],
        },
    ):
        app.dependency_overrides[get_db_session] = mock_db_session
        wallet = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
        try:
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/wallets/{wallet}/rewards/forecast",
                        headers={"X-Wallet-Address": wallet},
                    )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_estimate"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

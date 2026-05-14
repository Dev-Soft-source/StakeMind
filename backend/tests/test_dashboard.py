import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database.session import get_db_session  # noqa: E402
from app.ingestion.mvp_sync import CatalogSyncResult, PortfolioSyncResult  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead  # noqa: E402


def _validator_fixture() -> object:
    return type(
        "Validator",
        (),
        {
            "hotkey": "5StakeMind00100abc",
            "subnet_id": 1,
            "uid": 0,
            "metadata_json": {
                "display_name": "Validator 1-1",
                "reliability_score": 88,
                "apy_estimate": 12.5,
                "uptime_percent": 97.2,
                "reward_consistency": 0.91,
                "delegated_stake_rao": 1_500_000_000,
            },
        },
    )()


@pytest.mark.asyncio
async def test_wallet_scope_rejects_mismatched_header(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/wallets/5Alice/staking",
                headers={"X-Wallet-Address": "5Bob"},
            )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_validators_returns_paginated_payload(app) -> None:
    validator = _validator_fixture()

    with patch(
        "app.api.v1.dashboard.portfolio_service.list_validators",
        new_callable=AsyncMock,
        return_value=([validator], 1),
    ):
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/validators?page=1&page_size=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total_items"] == 1
    assert payload["data"][0]["display_name"] == "Validator 1-1"


@pytest.mark.asyncio
async def test_list_validators_uses_cached_payload(app) -> None:
    cached_payload = {
        "data": [
            {
                "hotkey": "cached",
                "subnet_id": 1,
                "uid": 0,
                "display_name": "Cached validator",
                "reliability_score": 80,
                "apy_estimate": 10.0,
                "uptime_percent": 99.0,
                "reward_consistency": 0.8,
                "delegated_stake_rao": 1,
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total_items": 1,
            "total_pages": 1,
        },
    }

    with patch(
        "app.api.v1.dashboard.portfolio_service.list_validators",
        new_callable=AsyncMock,
    ) as list_validators:
        with patch(
            "app.api.v1.dashboard.CacheService.get_json",
            new_callable=AsyncMock,
            return_value=cached_payload,
        ):
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/api/v1/validators")

    assert response.status_code == 200
    assert response.json()["data"][0]["hotkey"] == "cached"
    list_validators.assert_not_called()


@pytest.mark.asyncio
async def test_dashboard_smoke_flow(app) -> None:
    wallet_address = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
    validator = _validator_fixture()

    async def mock_db_session():
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    try:
        with patch(
            "app.api.v1.dashboard.portfolio_service.list_validators",
            new_callable=AsyncMock,
            return_value=([validator], 1),
        ):
            with patch(
                "app.api.v1.dashboard.portfolio_service.get_validator",
                new_callable=AsyncMock,
                return_value=validator,
            ):
                with patch(
                    "app.api.v1.dashboard.portfolio_service.list_stakes_for_wallet",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    with patch(
                        "app.api.v1.dashboard.portfolio_service.reward_summary",
                        new_callable=AsyncMock,
                        return_value={"total_rewards_rao": 0, "total_stake_rao": 0},
                    ):
                        with patch(
                            "app.api.v1.dashboard.portfolio_service.reward_history",
                            new_callable=AsyncMock,
                            return_value=[],
                        ):
                            with patch(
                                "app.api.v1.dashboard.fetch_chain_head",
                                new_callable=AsyncMock,
                                return_value=ChainHead(block_number=99, block_hash="0xabc"),
                            ):
                                with patch(
                                    "app.api.v1.dashboard.sync_wallet_portfolio",
                                    new_callable=AsyncMock,
                                    return_value=PortfolioSyncResult(
                                        wallet_address=wallet_address,
                                        chain_head=99,
                                        stakes_upserted=1,
                                        reward_points_written=3,
                                    ),
                                ):
                                    async with app.router.lifespan_context(app):
                                        transport = ASGITransport(app=app)
                                        async with AsyncClient(
                                            transport=transport,
                                            base_url="http://test",
                                        ) as client:
                                            validators = await client.get("/api/v1/validators")
                                            detail = await client.get(
                                                f"/api/v1/validators/{validator.hotkey}"
                                            )
                                            session = await client.post(
                                                "/api/v1/wallets/session",
                                                json={"wallet_address": wallet_address},
                                            )
                                            sync = await client.post(
                                                "/api/v1/ingestion/portfolio-sync",
                                                json={"wallet_address": wallet_address},
                                            )
                                            staking = await client.get(
                                                f"/api/v1/wallets/{wallet_address}/staking",
                                                headers={"X-Wallet-Address": wallet_address},
                                            )
                                            rewards = await client.get(
                                                f"/api/v1/wallets/{wallet_address}/rewards/summary",
                                                headers={"X-Wallet-Address": wallet_address},
                                            )
    finally:
        app.dependency_overrides.clear()

    assert validators.status_code == 200
    assert detail.status_code == 200
    assert session.status_code == 200
    assert sync.status_code == 200
    assert staking.status_code == 200
    assert rewards.status_code == 200


@pytest.mark.asyncio
async def test_catalog_sync_updates_watermark(app) -> None:
    with patch(
        "app.api.v1.dashboard.fetch_chain_head",
        new_callable=AsyncMock,
        return_value=ChainHead(block_number=123, block_hash="0xdef"),
    ):
        with patch(
            "app.api.v1.dashboard.sync_validator_catalog",
            new_callable=AsyncMock,
            return_value=CatalogSyncResult(
                chain_head=123,
                validators_upserted=4,
                subnets_processed=2,
            ),
        ):
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post("/api/v1/ingestion/catalog-sync")

    assert response.status_code == 200
    assert response.json()["chain_head"] == 123


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

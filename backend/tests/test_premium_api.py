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
        session.get = AsyncMock(return_value=None)
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = AsyncMock()
        session.flush = AsyncMock()
        yield session

    return _override


WALLET = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"


@pytest.mark.asyncio
async def test_premium_advanced_scores_requires_premium(app, mock_db_session) -> None:
    with patch(
        "app.api.v1.dependencies.is_wallet_premium",
        new_callable=AsyncMock,
        return_value=False,
    ):
        app.dependency_overrides[get_db_session] = mock_db_session
        try:
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/premium/wallets/{WALLET}/advanced-scores",
                        headers={"X-Wallet-Address": WALLET},
                    )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_premium_advanced_scores_ok_when_entitled(app, mock_db_session) -> None:
    rollup = type(
        "R",
        (),
        {
            "hotkey": "5Hk",
            "subnet_id": 1,
            "composite_score": 80,
            "reputation_signal": 0.9,
            "apy_estimate": 10.0,
        },
    )()

    with patch(
        "app.api.v1.dependencies.is_wallet_premium",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with patch(
            "app.api.v1.premium.list_rankings",
            new_callable=AsyncMock,
            return_value=([rollup], 1),
        ):
            app.dependency_overrides[get_db_session] = mock_db_session
            try:
                async with app.router.lifespan_context(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        response = await client.get(
                            f"/api/v1/premium/wallets/{WALLET}/advanced-scores",
                            headers={"X-Wallet-Address": WALLET},
                        )
            finally:
                app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["composite_score"] == 80
    assert "optimization_score" in body["data"][0]


@pytest.mark.asyncio
async def test_read_entitlements_returns_free_without_row(app, mock_db_session) -> None:
    app.dependency_overrides[get_db_session] = mock_db_session
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/wallets/{WALLET}/entitlements",
                    headers={"X-Wallet-Address": WALLET},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["plan"] == "free"


@pytest.mark.asyncio
async def test_redeem_invite_wallet_scope_mismatch(app, mock_db_session) -> None:
    other = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
    app.dependency_overrides[get_db_session] = mock_db_session
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/wallets/{WALLET}/entitlements/redeem-invite",
                    headers={"X-Wallet-Address": other},
                    json={"code": "TEST-CODE"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_redeem_invite_success(app, mock_db_session) -> None:
    fake_redeem = AsyncMock(return_value=object())
    with patch("app.api.v1.entitlements.redeem_invite_code", fake_redeem):
        with patch(
            "app.api.v1.entitlements.audit_service.record_audit_event",
            new_callable=AsyncMock,
        ):
            app.dependency_overrides[get_db_session] = mock_db_session
            try:
                async with app.router.lifespan_context(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        response = await client.post(
                            f"/api/v1/wallets/{WALLET}/entitlements/redeem-invite",
                            headers={"X-Wallet-Address": WALLET},
                            json={"code": "TEST-INVITE"},
                        )
            finally:
                app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["plan"] == "premium"
    assert fake_redeem.await_count == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

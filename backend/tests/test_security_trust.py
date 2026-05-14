import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.database.session import get_db_session
from app.main import create_app


@pytest.mark.asyncio
async def test_security_headers_on_api_response(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/automation/legal")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


@pytest.mark.asyncio
async def test_rate_limit_returns_429_when_enabled() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self._counts: dict[str, int] = {}

        async def incr(self, key: str) -> int:
            self._counts[key] = self._counts.get(key, 0) + 1
            return self._counts[key]

        async def expire(self, key: str, seconds: int) -> bool:
            return True

        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            return None

    unique_ip = f"198.51.100.{uuid.uuid4().int % 200 + 1}"
    settings = Settings(
        environment="test",
        database_url="postgresql://stakemind:stakemind@localhost:5432/stakemind",
        redis_url="redis://localhost:6379/0",
        rate_limit_enabled=True,
        rate_limit_per_minute=2,
        trust_x_forwarded_for=True,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        await app.state.redis.aclose()
        app.state.redis = _FakeRedis()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Forwarded-For": unique_ip}
            url = "/api/v1/automation/legal"
            r1 = await client.get(url, headers=headers)
            r2 = await client.get(url, headers=headers)
            assert r1.status_code == 200
            assert r2.status_code == 200
            third = await client.get(url, headers=headers)
    assert third.status_code == 429
    body = third.json()
    assert body["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_invalid_json_returns_422(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/wallets/session",
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_wallet_risk_requires_matching_header(app) -> None:
    from unittest.mock import AsyncMock

    async def _override():
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))
        yield session

    wallet = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
    other = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
    app.dependency_overrides[get_db_session] = _override
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

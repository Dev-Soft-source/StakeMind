import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://stakemind:stakemind@localhost:5432/stakemind",
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def app(test_settings: Settings):
    return create_app(test_settings)


@pytest.mark.asyncio
async def test_health_endpoint_reports_service_metadata(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "StakeMind API"
    assert payload["version"] == "0.1.0"
    assert "checks" in payload

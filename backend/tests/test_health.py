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


@pytest.mark.asyncio
async def test_pagination_contract_matches_versioned_shape(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/contracts/pagination?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 20,
        "total_items": 0,
        "total_pages": 0,
    }


@pytest.mark.asyncio
async def test_openapi_documents_error_and_pagination_schemas(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "ErrorResponse" in schema["components"]["schemas"]
    assert any(name.startswith("PaginatedResponse") for name in schema["components"]["schemas"])

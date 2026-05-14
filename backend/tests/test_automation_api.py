import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_automation_legal_public(app) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/automation/legal")
    assert response.status_code == 200
    assert "disclaimer" in response.json()

"""Integration-style API tests for ingestion routes (ASGI + mocked DB + RPC)."""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database.session import get_db_session  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead  # noqa: E402


@pytest.mark.asyncio
async def test_chain_head_sync_api_returns_contract_fields(app) -> None:
    async def _db():
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        yield session

    class FakeRpc:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=55, block_hash="0xsync")

    app.state.rpc_client_factory = lambda settings: FakeRpc()
    app.dependency_overrides[get_db_session] = _db

    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/integrations/subtensor/ingestion/chain-head-sync",
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {
        "idempotency_key",
        "chain_head",
        "status",
        "subnets_seeded",
        "reused_existing",
    }
    assert body["chain_head"] == 55
    assert body["idempotency_key"] == "chain-head-sync:0xsync"


@pytest.mark.asyncio
async def test_chain_head_sync_reuses_cached_run_response_shape(app) -> None:
    from app.database.models import IngestionRun

    existing = IngestionRun(
        job_name="chain_head_sync",
        idempotency_key="chain-head-sync:0xcache",
        chain_head=100,
        status="succeeded",
    )

    async def _db():
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=existing)
        yield session

    class FakeRpc:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=200, block_hash="0xcache")

    app.state.rpc_client_factory = lambda settings: FakeRpc()
    app.dependency_overrides[get_db_session] = _db

    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/integrations/subtensor/ingestion/chain-head-sync",
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["reused_existing"] is True
    assert payload["subnets_seeded"] == 0
    assert payload["status"] == "succeeded"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

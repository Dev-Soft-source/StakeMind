"""Failure drills: RPC outage surfaces at API boundary; ingestion idempotency vs stale head."""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database.models import IngestionRun  # noqa: E402
from app.database.session import get_db_session  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcError  # noqa: E402


@pytest.mark.asyncio
async def test_chain_head_get_returns_500_when_rpc_head_unavailable(app) -> None:
    class DownRpc:
        async def fetch_chain_head(self) -> ChainHead:
            raise SubtensorRpcError("entrypoint unreachable")

        async def fetch_chain_name(self) -> str:
            return "finney"

    app.state.rpc_client_factory = lambda settings: DownRpc()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/integrations/subtensor/chain-head")

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_chain_head_get_ok_when_name_rpc_fails(app) -> None:
    class PartialRpc:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=1, block_hash="0x1")

        async def fetch_chain_name(self) -> str:
            raise SubtensorRpcError("system_chain down")

    app.state.rpc_client_factory = lambda settings: PartialRpc()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/integrations/subtensor/chain-head")

    assert response.status_code == 200
    assert response.json()["chain_name"] is None


@pytest.mark.asyncio
async def test_chain_head_sync_returns_500_when_rpc_head_unavailable(app) -> None:
    class DownRpc:
        async def fetch_chain_head(self) -> ChainHead:
            raise SubtensorRpcError("timeout")

    async def _db():
        from unittest.mock import AsyncMock

        session = AsyncMock()
        yield session

    app.state.rpc_client_factory = lambda settings: DownRpc()
    app.dependency_overrides[get_db_session] = _db

    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/integrations/subtensor/ingestion/chain-head-sync",
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_stale_indexer_reuses_prior_success_for_same_block_hash(app) -> None:
    """Same block hash as a completed run: API reports reuse (no duplicate subnet seed)."""

    async def _db():
        from unittest.mock import AsyncMock

        existing = IngestionRun(
            job_name="chain_head_sync",
            idempotency_key="chain-head-sync:0xstale",
            chain_head=50,
            status="succeeded",
        )
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=existing)
        yield session

    class Rpc:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=999, block_hash="0xstale")

    app.state.rpc_client_factory = lambda settings: Rpc()
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
    assert body["reused_existing"] is True
    assert body["chain_head"] == 50


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

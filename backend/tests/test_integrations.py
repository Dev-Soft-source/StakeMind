import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcClient, SubtensorRpcError


@pytest.mark.asyncio
async def test_rpc_client_retries_until_success() -> None:
    calls = {"count": 0}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"result": "ok"}

    class FakeClient:
        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            calls["count"] += 1
            if calls["count"] < 3:
                raise httpx.TimeoutException("temporary timeout")
            return FakeResponse()

    client = SubtensorRpcClient(
        rpc_url="https://example.invalid",
        timeout_seconds=1.0,
        max_retries=3,
        client=FakeClient(),  # type: ignore[arg-type]
    )

    result = await client.call("system_chain")
    assert result == "ok"
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_rpc_client_raises_after_retry_budget() -> None:
    class FailingClient:
        async def post(self, url: str, json: dict[str, object]) -> None:
            raise httpx.TimeoutException("still timing out")

    client = SubtensorRpcClient(
        rpc_url="https://example.invalid",
        timeout_seconds=1.0,
        max_retries=1,
        client=FailingClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(SubtensorRpcError):
        await client.call("chain_getHeader")


@pytest.mark.asyncio
async def test_chain_head_endpoint_returns_block_metadata(app) -> None:
    class FakeRpcClient:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=42, block_hash="0xabc")

        async def fetch_chain_name(self) -> str:
            return "Bittensor"

    app.state.rpc_client_factory = lambda settings: FakeRpcClient()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/integrations/subtensor/chain-head")

    assert response.status_code == 200
    payload = response.json()
    assert payload["block_number"] == 42
    assert payload["block_hash"] == "0xabc"
    assert payload["chain_name"] == "Bittensor"

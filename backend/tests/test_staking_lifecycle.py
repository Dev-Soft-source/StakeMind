"""Integration-style staking lifecycle checks (ASGI + mocked DB + RPC)."""

import sys
from pathlib import Path
from uuid import uuid4

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database.session import get_db_session  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead  # noqa: E402

WALLET = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
DEST = "5StakeMind00100abc1234567890abcdef1234567890ab"


@pytest.mark.asyncio
async def test_delegate_build_then_submit_sequence(app) -> None:
    """Build returns an id; submit with same wallet + idempotency succeeds once."""

    async def mock_db_session():
        session = AsyncMock()
        session.add = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))
        yield session

    class FakeRpcClient:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=42, block_hash="0xabc")

        async def fetch_chain_name(self) -> str:
            return "Bittensor"

    tx_id = uuid4()
    built = type(
        "StakingTransaction",
        (),
        {
            "id": tx_id,
            "wallet_address": WALLET,
            "action": "delegate",
            "subnet_id": 1,
            "amount_rao": 1_000_000_000,
            "source_validator_hotkey": None,
            "dest_validator_hotkey": DEST,
            "status": "built",
            "unsigned_payload": {"version": 1, "call": {"method": "add_stake"}},
            "simulation_result": {
                "supported": True,
                "status": "ok",
                "message": "ok",
                "estimated_fee_rao": 1_000_000,
                "block_number": 42,
            },
            "tx_hash": None,
            "failure_reason": None,
            "expires_at": "2026-01-01T00:00:00+00:00",
            "submitted_at": None,
            "confirmed_at": None,
        },
    )()

    confirmed = type(
        "StakingTransaction",
        (),
        {
            "id": tx_id,
            "wallet_address": WALLET,
            "action": "delegate",
            "subnet_id": 1,
            "amount_rao": 1_000_000_000,
            "source_validator_hotkey": None,
            "dest_validator_hotkey": DEST,
            "status": "confirmed",
            "unsigned_payload": {"version": 1},
            "simulation_result": {"supported": True, "status": "ok", "message": "ok"},
            "tx_hash": "0xdeadbeef",
            "failure_reason": None,
            "expires_at": "2026-01-01T00:00:00+00:00",
            "submitted_at": "2026-01-01T00:00:01+00:00",
            "confirmed_at": "2026-01-01T00:00:02+00:00",
        },
    )()

    app.state.rpc_client_factory = lambda settings: FakeRpcClient()
    app.dependency_overrides[get_db_session] = mock_db_session

    with patch(
        "app.api.v1.staking.build_transaction",
        new_callable=AsyncMock,
        return_value=built,
    ):
        with patch(
            "app.api.v1.staking.get_transaction",
            new_callable=AsyncMock,
            return_value=confirmed,
        ):
            with patch(
                "app.api.v1.staking.submit_transaction",
                new_callable=AsyncMock,
                return_value=confirmed,
            ) as submit_transaction:
                try:
                    async with app.router.lifespan_context(app):
                        transport = ASGITransport(app=app)
                        async with AsyncClient(
                            transport=transport, base_url="http://test"
                        ) as client:
                            build_resp = await client.post(
                                "/api/v1/staking/transactions/build",
                                headers={"X-Wallet-Address": WALLET},
                                json={
                                    "wallet_address": WALLET,
                                    "action": "delegate",
                                    "subnet_id": 1,
                                    "amount_rao": 1_000_000_000,
                                    "dest_validator_hotkey": DEST,
                                },
                            )
                            assert build_resp.status_code == 200
                            submit_resp = await client.post(
                                f"/api/v1/staking/transactions/{tx_id}/submit",
                                headers={
                                    "X-Wallet-Address": WALLET,
                                    "Idempotency-Key": "lifecycle-1",
                                },
                                json={"tx_hash": "0xdeadbeef"},
                            )
                finally:
                    app.dependency_overrides.clear()

    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "confirmed"
    submit_transaction.assert_awaited_once()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

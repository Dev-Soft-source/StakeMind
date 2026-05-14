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

WALLET_ALICE = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
WALLET_BOB = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
DEST_HOTKEY = "5StakeMind00100abc1234567890abcdef1234567890ab"


@pytest.fixture
def mock_db_session():
    async def _override():
        session = AsyncMock()
        session.add = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))
        yield session

    return _override


@pytest.mark.asyncio
async def test_build_staking_transaction_requires_wallet_scope(app, mock_db_session) -> None:
    app.dependency_overrides[get_db_session] = mock_db_session
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/staking/transactions/build",
                    headers={"X-Wallet-Address": WALLET_BOB},
                    json={
                        "wallet_address": WALLET_ALICE,
                        "action": "delegate",
                        "subnet_id": 1,
                        "amount_rao": 1_000_000_000,
                        "dest_validator_hotkey": DEST_HOTKEY,
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_build_staking_transaction_returns_unsigned_payload(app, mock_db_session) -> None:
    class FakeRpcClient:
        async def fetch_chain_head(self) -> ChainHead:
            return ChainHead(block_number=42, block_hash="0xabc")

        async def fetch_chain_name(self) -> str:
            return "Bittensor"

    app.state.rpc_client_factory = lambda settings: FakeRpcClient()
    app.dependency_overrides[get_db_session] = mock_db_session

    built_transaction = type(
        "StakingTransaction",
        (),
        {
            "id": uuid4(),
            "wallet_address": WALLET_ALICE,
            "action": "delegate",
            "subnet_id": 1,
            "amount_rao": 1_000_000_000,
            "source_validator_hotkey": None,
            "dest_validator_hotkey": DEST_HOTKEY,
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

    with patch(
        "app.api.v1.staking.build_transaction",
        new_callable=AsyncMock,
        return_value=built_transaction,
    ):
        try:
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/staking/transactions/build",
                        headers={"X-Wallet-Address": WALLET_ALICE},
                        json={
                            "wallet_address": WALLET_ALICE,
                            "action": "delegate",
                            "subnet_id": 1,
                            "amount_rao": 1_000_000_000,
                            "dest_validator_hotkey": DEST_HOTKEY,
                        },
                    )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "built"
    assert payload["unsigned_payload"]["call"]["method"] == "add_stake"


@pytest.mark.asyncio
async def test_submit_staking_transaction_is_idempotent(app, mock_db_session) -> None:
    transaction_id = uuid4()
    submitted_transaction = type(
        "StakingTransaction",
        (),
        {
            "id": transaction_id,
            "wallet_address": WALLET_ALICE,
            "action": "delegate",
            "subnet_id": 1,
            "amount_rao": 1_000_000_000,
            "source_validator_hotkey": None,
            "dest_validator_hotkey": DEST_HOTKEY,
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

    with patch(
        "app.api.v1.staking.get_transaction",
        new_callable=AsyncMock,
        return_value=submitted_transaction,
    ):
        with patch(
            "app.api.v1.staking.submit_transaction",
            new_callable=AsyncMock,
            return_value=submitted_transaction,
        ) as submit_transaction:
            app.dependency_overrides[get_db_session] = mock_db_session
            try:
                async with app.router.lifespan_context(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        response = await client.post(
                            f"/api/v1/staking/transactions/{transaction_id}/submit",
                            headers={
                                "X-Wallet-Address": WALLET_ALICE,
                                "Idempotency-Key": "idem-1",
                            },
                            json={"tx_hash": "0xdeadbeef"},
                        )
            finally:
                app.dependency_overrides.clear()

    assert response.status_code == 200
    submit_transaction.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_staking_transaction_requires_idempotency_key(app, mock_db_session) -> None:
    app.dependency_overrides[get_db_session] = mock_db_session
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/staking/transactions/{uuid4()}/submit",
                    headers={"X-Wallet-Address": WALLET_ALICE},
                    json={"tx_hash": "0xdeadbeef"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

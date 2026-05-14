import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.database.models import IngestionRun  # noqa: E402
from app.ingestion.chain_head import _seed_subnet_catalog, sync_chain_head  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead  # noqa: E402


def _session_mock() -> AsyncMock:
    """Async session mock with sync ``add`` (matches real AsyncSession.add)."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_sync_chain_head_reuses_existing_run() -> None:
    session = _session_mock()
    existing = IngestionRun(
        job_name="chain_head_sync",
        idempotency_key="chain-head-sync:0xabc",
        chain_head=42,
        status="succeeded",
    )
    session.scalar = AsyncMock(return_value=existing)
    rpc_client = AsyncMock()
    rpc_client.fetch_chain_head = AsyncMock(
        return_value=ChainHead(block_number=42, block_hash="0xabc")
    )

    result = await sync_chain_head(session, rpc_client, subnet_limit=16)

    assert result.reused_existing is True
    assert result.subnets_seeded == 0
    assert result.status == "succeeded"
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_seed_subnet_catalog_is_bounded_by_limit() -> None:
    session = _session_mock()
    session.get = AsyncMock(return_value=None)

    seeded = await _seed_subnet_catalog(session, subnet_limit=4)

    assert seeded == 4
    assert session.add.call_count == 4


@pytest.mark.asyncio
async def test_sync_chain_head_seeds_subnets_on_first_run() -> None:
    session = _session_mock()
    session.scalar = AsyncMock(return_value=None)
    session.get = AsyncMock(return_value=None)
    rpc_client = AsyncMock()
    rpc_client.fetch_chain_head = AsyncMock(
        return_value=ChainHead(block_number=7, block_hash="0xdef")
    )

    result = await sync_chain_head(session, rpc_client, subnet_limit=3)

    assert result.reused_existing is False
    assert result.chain_head == 7
    assert result.subnets_seeded == 3
    assert result.status == "succeeded"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_chain_head_propagates_rpc_failure() -> None:
    from app.integrations.bittensor.rpc import SubtensorRpcError

    session = AsyncMock()
    rpc_client = AsyncMock()
    rpc_client.fetch_chain_head = AsyncMock(side_effect=SubtensorRpcError("rpc unavailable"))

    with pytest.raises(SubtensorRpcError, match="rpc unavailable"):
        await sync_chain_head(session, rpc_client, subnet_limit=2)


@pytest.mark.asyncio
async def test_sync_chain_head_handles_flush_integrity_race() -> None:
    existing = IngestionRun(
        job_name="chain_head_sync",
        idempotency_key="chain-head-sync:0xrace",
        chain_head=10,
        status="succeeded",
    )
    session = _session_mock()
    session.scalar = AsyncMock(side_effect=[None, existing])
    session.flush = AsyncMock(side_effect=IntegrityError("stmt", None, Exception("dup")))
    session.rollback = AsyncMock()
    rpc_client = AsyncMock()
    rpc_client.fetch_chain_head = AsyncMock(
        return_value=ChainHead(block_number=10, block_hash="0xrace")
    )

    result = await sync_chain_head(session, rpc_client, subnet_limit=2)

    assert result.reused_existing is True
    assert result.subnets_seeded == 0
    assert result.status == "succeeded"
    session.rollback.assert_awaited_once()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

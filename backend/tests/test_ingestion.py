from unittest.mock import AsyncMock

import pytest

from app.database.models import IngestionRun
from app.ingestion.chain_head import _seed_subnet_catalog, sync_chain_head
from app.integrations.bittensor.rpc import ChainHead


@pytest.mark.asyncio
async def test_sync_chain_head_reuses_existing_run() -> None:
    session = AsyncMock()
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
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    seeded = await _seed_subnet_catalog(session, subnet_limit=4)

    assert seeded == 4
    assert session.add.call_count == 4


@pytest.mark.asyncio
async def test_sync_chain_head_seeds_subnets_on_first_run() -> None:
    session = AsyncMock()
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

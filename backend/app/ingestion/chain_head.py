from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import IngestionRun, Subnet
from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcClient


@dataclass(frozen=True)
class IngestionResult:
    idempotency_key: str
    chain_head: int
    status: str
    subnets_seeded: int
    reused_existing: bool


async def sync_chain_head(
    session: AsyncSession,
    rpc_client: SubtensorRpcClient,
    subnet_limit: int,
) -> IngestionResult:
    chain_head: ChainHead = await rpc_client.fetch_chain_head()
    idempotency_key = f"chain-head-sync:{chain_head.block_hash}"

    existing = await session.scalar(
        select(IngestionRun).where(IngestionRun.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return IngestionResult(
            idempotency_key=existing.idempotency_key,
            chain_head=existing.chain_head or chain_head.block_number,
            status=existing.status,
            subnets_seeded=0,
            reused_existing=True,
        )

    run = IngestionRun(
        job_name="chain_head_sync",
        idempotency_key=idempotency_key,
        chain_head=chain_head.block_number,
        status="running",
    )
    session.add(run)

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(IngestionRun).where(IngestionRun.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        return IngestionResult(
            idempotency_key=existing.idempotency_key,
            chain_head=existing.chain_head or chain_head.block_number,
            status=existing.status,
            subnets_seeded=0,
            reused_existing=True,
        )

    subnets_seeded = await _seed_subnet_catalog(session, subnet_limit)
    run.status = "succeeded"
    run.detail = f"Seeded {subnets_seeded} subnet placeholders"
    run.finished_at = datetime.now(UTC)
    await session.commit()

    return IngestionResult(
        idempotency_key=run.idempotency_key,
        chain_head=chain_head.block_number,
        status=run.status,
        subnets_seeded=subnets_seeded,
        reused_existing=False,
    )


async def _seed_subnet_catalog(session: AsyncSession, subnet_limit: int) -> int:
    seeded = 0
    for netuid in range(max(subnet_limit, 0)):
        existing = await session.get(Subnet, netuid)
        if existing is not None:
            continue
        session.add(Subnet(id=netuid, name=f"subnet-{netuid}", is_active=True))
        seeded += 1
    return seeded

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.session import get_db_session
from app.ingestion.chain_head import IngestionResult, sync_chain_head
from app.integrations.bittensor.rpc import ChainHead, SubtensorRpcClient

router = APIRouter(prefix="/integrations/subtensor", tags=["integrations"])


class ChainHeadResponse(BaseModel):
    block_number: int
    block_hash: str
    chain_name: str | None = None


class IngestionRunResponse(BaseModel):
    idempotency_key: str
    chain_head: int
    status: str
    subnets_seeded: int
    reused_existing: bool


def build_rpc_client(settings: Settings, request: Request | None = None) -> SubtensorRpcClient:
    if request is not None:
        factory = getattr(request.app.state, "rpc_client_factory", None)
        if factory is not None:
            return factory(settings)
    return SubtensorRpcClient(
        rpc_url=settings.bittensor_rpc_url,
        timeout_seconds=settings.bittensor_rpc_timeout_seconds,
        max_retries=settings.bittensor_rpc_max_retries,
    )


@router.get("/chain-head", response_model=ChainHeadResponse)
async def read_chain_head(request: Request) -> ChainHeadResponse:
    settings: Settings = request.app.state.settings
    client = build_rpc_client(settings, request)
    chain_head: ChainHead = await client.fetch_chain_head()
    chain_name: str | None = None
    try:
        chain_name = await client.fetch_chain_name()
    except Exception:
        chain_name = None
    return ChainHeadResponse(
        block_number=chain_head.block_number,
        block_hash=chain_head.block_hash,
        chain_name=chain_name,
    )


@router.post("/ingestion/chain-head-sync", response_model=IngestionRunResponse)
async def run_chain_head_sync(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IngestionRunResponse:
    settings: Settings = request.app.state.settings
    client = build_rpc_client(settings, request)
    result: IngestionResult = await sync_chain_head(
        session,
        client,
        settings.bittensor_ingestion_subnet_limit,
    )
    return IngestionRunResponse(
        idempotency_key=result.idempotency_key,
        chain_head=result.chain_head,
        status=result.status,
        subnets_seeded=result.subnets_seeded,
        reused_existing=result.reused_existing,
    )

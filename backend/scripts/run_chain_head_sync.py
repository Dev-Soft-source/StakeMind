import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.ingestion.chain_head import sync_chain_head
from app.integrations.bittensor.rpc import SubtensorRpcClient


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    client = SubtensorRpcClient(
        rpc_url=settings.bittensor_rpc_url,
        timeout_seconds=settings.bittensor_rpc_timeout_seconds,
        max_retries=settings.bittensor_rpc_max_retries,
    )

    async with session_factory() as session:
        result = await sync_chain_head(
            session,
            client,
            settings.bittensor_ingestion_subnet_limit,
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())

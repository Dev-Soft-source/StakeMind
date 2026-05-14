import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.ingestion.chain_head import sync_chain_head
from app.ingestion.intelligence_recompute import recompute_intelligence
from app.ingestion.mvp_sync import fetch_chain_head, sync_validator_catalog, sync_wallet_portfolio
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

    default_wallet = "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC"
    wallet_address = sys.argv[1] if len(sys.argv) > 1 else default_wallet

    async with session_factory() as session:
        chain_head_result = await sync_chain_head(
            session,
            client,
            settings.bittensor_ingestion_subnet_limit,
        )
        chain_head = await fetch_chain_head(client)
        catalog_result = await sync_validator_catalog(session, chain_head)
        portfolio_result = await sync_wallet_portfolio(session, wallet_address, chain_head)
        intelligence_result = await recompute_intelligence(
            session,
            chain_head,
            window_days=settings.intelligence_recompute_window_days,
        )

    print(
        {
            "chain_head_sync": chain_head_result,
            "catalog_sync": catalog_result,
            "portfolio_sync": portfolio_result,
            "intelligence_recompute": intelligence_result,
        }
    )


if __name__ == "__main__":
    asyncio.run(main())

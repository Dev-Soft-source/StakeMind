"""Poll automation_jobs and run handlers (separate durable worker process)."""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.automation.worker import process_next_job


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    sleep_s = 5
    while True:
        async with session_factory() as session:
            worked = await process_next_job(session)
            await session.commit()
        if not worked:
            await asyncio.sleep(sleep_s)


if __name__ == "__main__":
    asyncio.run(main())

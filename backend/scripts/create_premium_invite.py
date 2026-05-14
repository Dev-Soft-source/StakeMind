"""Create a premium invite code row (operator script)."""

import asyncio
import secrets
import sys
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.database.models import PremiumInviteCode


async def main() -> None:
    settings = get_settings()
    max_redemptions = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    code = sys.argv[2] if len(sys.argv) > 2 else f"STAKEMIND-PREMIUM-{secrets.token_hex(4).upper()}"

    engine = create_async_engine(settings.async_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        invite = PremiumInviteCode(
            id=uuid4(),
            code=code.strip(),
            max_redemptions=max_redemptions,
            redemptions_count=0,
            expires_at=None,
        )
        session.add(invite)
        await session.commit()
        print({"code": invite.code, "max_redemptions": invite.max_redemptions})


if __name__ == "__main__":
    asyncio.run(main())

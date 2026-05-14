from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.session import get_db_session
from app.integrations.bittensor.rpc import SubtensorRpcClient
from app.services.premium.entitlements import is_wallet_premium


def build_rpc_client(settings: Settings, request: Request) -> SubtensorRpcClient:
    factory = getattr(request.app.state, "rpc_client_factory", None)
    if factory is not None:
        return factory(settings)
    return SubtensorRpcClient(
        rpc_url=settings.bittensor_rpc_url,
        timeout_seconds=settings.bittensor_rpc_timeout_seconds,
        max_retries=settings.bittensor_rpc_max_retries,
    )


def assert_wallet_scope(path_wallet: str, header_wallet: str | None) -> None:
    if header_wallet and header_wallet != path_wallet:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet header does not match requested address",
        )


async def require_premium_scoped_wallet(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> None:
    assert_wallet_scope(wallet_address, x_wallet_address)
    if not await is_wallet_premium(session, wallet_address):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium entitlement required",
        )

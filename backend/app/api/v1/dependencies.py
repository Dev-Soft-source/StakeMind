from fastapi import HTTPException, Request, status

from app.core.config import Settings
from app.integrations.bittensor.rpc import SubtensorRpcClient


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

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.integrations.bittensor.rpc import SubtensorRpcClient


async def main() -> int:
    settings = get_settings()
    client = SubtensorRpcClient(
        rpc_url=settings.bittensor_rpc_url,
        timeout_seconds=settings.bittensor_rpc_timeout_seconds,
        max_retries=settings.bittensor_rpc_max_retries,
    )

    chain_head = await client.fetch_chain_head()
    chain_name = await client.fetch_chain_name()
    print(f"chain_name={chain_name}")
    print(f"block_number={chain_head.block_number}")
    print(f"block_hash={chain_head.block_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

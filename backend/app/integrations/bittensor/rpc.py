from dataclasses import dataclass

import httpx


class SubtensorRpcError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChainHead:
    block_number: int
    block_hash: str


class SubtensorRpcClient:
    def __init__(
        self,
        rpc_url: str,
        timeout_seconds: float,
        max_retries: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._rpc_url = rpc_url
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._client = client

    async def call(self, method: str, params: list[object] | None = None) -> object:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or [],
        }
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                if self._client is not None:
                    response = await self._client.post(self._rpc_url, json=payload)
                else:
                    async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                        response = await client.post(self._rpc_url, json=payload)
                response.raise_for_status()
                body = response.json()
                if body.get("error"):
                    raise SubtensorRpcError(str(body["error"]))
                return body["result"]
            except (httpx.TimeoutException, httpx.TransportError, SubtensorRpcError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                continue

        raise SubtensorRpcError(f"RPC call failed for {method}") from last_error

    async def fetch_chain_head(self) -> ChainHead:
        header = await self.call("chain_getHeader")
        if not isinstance(header, dict):
            raise SubtensorRpcError("Unexpected chain_getHeader response")
        number = header.get("number")
        if not isinstance(number, str):
            raise SubtensorRpcError("Missing block number in chain_getHeader response")
        block_hash = await self.call("chain_getBlockHash", [number])
        if not isinstance(block_hash, str):
            raise SubtensorRpcError("Missing block hash in chain_getBlockHash response")
        return ChainHead(block_number=int(number, 16), block_hash=block_hash)

    async def fetch_chain_name(self) -> str:
        result = await self.call("system_chain")
        if not isinstance(result, str):
            raise SubtensorRpcError("Unexpected system_chain response")
        return result

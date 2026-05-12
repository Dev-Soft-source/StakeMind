import json
from typing import Any

from redis.asyncio import Redis

from app.cache.redis import cache_key


class CacheService:
    def __init__(self, redis: Redis, default_ttl_seconds: int) -> None:
        self._redis = redis
        self._default_ttl_seconds = default_ttl_seconds

    async def get_json(self, namespace: str, *parts: str) -> Any | None:
        raw = await self._redis.get(cache_key(namespace, *parts))
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(
        self,
        namespace: str,
        value: Any,
        *parts: str,
        ttl_seconds: int | None = None,
    ) -> None:
        await self._redis.set(
            cache_key(namespace, *parts),
            json.dumps(value),
            ex=ttl_seconds or self._default_ttl_seconds,
        )

"""Redis cache helpers and TTL conventions for StakeMind."""

from redis.asyncio import Redis

# Default TTLs are configured via Settings:
# - REDIS_DEFAULT_TTL_SECONDS: validator catalog and aggregate reads
# - REDIS_SESSION_TTL_SECONDS: wallet session and rate-limit buckets


def create_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=True)


def cache_key(namespace: str, *parts: str) -> str:
    return ":".join(("stakemind", namespace, *parts))

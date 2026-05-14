"""Optional Redis-backed per-IP rate limiting for API routes."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.v1.schemas.common import ErrorBody, ErrorResponse
from app.cache.redis import cache_key


def _client_ip(request: Request, trust_x_forwarded_for: bool) -> str:
    if trust_x_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:128] or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _should_skip_rate_limit(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if not path.startswith("/api/v1"):
        return True
    if path == "/api/v1/health" or path == "/api/v1/openapi.json":
        return True
    if path.startswith("/api/v1/docs") or path.startswith("/api/v1/redoc"):
        return True
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = request.app.state.settings
        if not getattr(settings, "rate_limit_enabled", False):
            return await call_next(request)

        path = request.url.path
        if _should_skip_rate_limit(path, request.method):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        ip = _client_ip(request, getattr(settings, "trust_x_forwarded_for", False))
        minute = int(time.time()) // 60
        limit = int(getattr(settings, "rate_limit_per_minute", 120))
        key = cache_key("ratelimit", str(minute), ip)

        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 120)
        except Exception:
            return await call_next(request)

        if count > limit:
            payload = ErrorResponse(
                error=ErrorBody(
                    code="rate_limited",
                    message="Too many requests; try again shortly.",
                )
            )
            return JSONResponse(status_code=429, content=payload.model_dump())

        return await call_next(request)

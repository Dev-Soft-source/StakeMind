from typing import Any

from fastapi import APIRouter, Request
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    checks: dict[str, str] = {"api": "ok"}
    overall = "ok"

    engine: AsyncEngine | None = getattr(request.app.state, "db_engine", None)
    if engine is None:
        checks["database"] = "unavailable"
        overall = "degraded"
    else:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
            overall = "degraded"

    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        checks["redis"] = "unavailable"
        overall = "degraded"
    else:
        try:
            if await redis.ping():
                checks["redis"] = "ok"
            else:
                checks["redis"] = "error"
                overall = "degraded"
        except Exception:
            checks["redis"] = "error"
            overall = "degraded"

    return {
        "status": overall,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": checks,
    }

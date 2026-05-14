from fastapi import APIRouter

from app.api.v1 import (
    automation,
    contracts,
    dashboard,
    entitlements,
    health,
    integrations,
    intelligence,
    premium,
    staking,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(integrations.router)
api_router.include_router(dashboard.router)
api_router.include_router(entitlements.router)
api_router.include_router(staking.router)
api_router.include_router(intelligence.router)
api_router.include_router(premium.router)
api_router.include_router(automation.router)

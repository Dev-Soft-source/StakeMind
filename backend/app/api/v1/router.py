from fastapi import APIRouter

from app.api.v1 import contracts, dashboard, health, integrations, intelligence, staking

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(integrations.router)
api_router.include_router(dashboard.router)
api_router.include_router(staking.router)
api_router.include_router(intelligence.router)

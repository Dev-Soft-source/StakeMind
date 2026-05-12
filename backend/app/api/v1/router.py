from fastapi import APIRouter

from app.api.v1 import contracts, health, integrations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(integrations.router)

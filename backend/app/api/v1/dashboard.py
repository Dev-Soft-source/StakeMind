from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.common import PaginatedResponse, PaginationMeta
from app.cache.redis import cache_key, invalidate_namespace
from app.core.config import Settings
from app.database.session import get_db_session
from app.ingestion.mvp_sync import fetch_chain_head, sync_validator_catalog, sync_wallet_portfolio
from app.integrations.bittensor.rpc import SubtensorRpcClient
from app.services import portfolio as portfolio_service
from app.services.cache import CacheService

router = APIRouter(tags=["validators"])


class ValidatorResponse(BaseModel):
    hotkey: str
    subnet_id: int
    uid: int | None
    display_name: str
    reliability_score: int
    apy_estimate: float
    uptime_percent: float
    reward_consistency: float
    delegated_stake_rao: int


class WalletSessionRequest(BaseModel):
    wallet_address: str = Field(min_length=10, max_length=128)


class WalletSessionResponse(BaseModel):
    wallet_address: str
    expires_at: str


class StakePositionResponse(BaseModel):
    validator_hotkey: str
    subnet_id: int
    amount_rao: int


class StakingPortfolioResponse(BaseModel):
    wallet_address: str
    total_stake_rao: int
    positions: list[StakePositionResponse]
    subnet_exposure: dict[str, int]


class RewardSummaryResponse(BaseModel):
    wallet_address: str
    total_rewards_rao: int
    total_stake_rao: int


class RewardHistoryPoint(BaseModel):
    captured_at: str
    amount_rao: int
    subnet_id: int
    validator_hotkey: str | None


def build_rpc_client(settings: Settings, request: Request) -> SubtensorRpcClient:
    factory = getattr(request.app.state, "rpc_client_factory", None)
    if factory is not None:
        return factory(settings)
    return SubtensorRpcClient(
        rpc_url=settings.bittensor_rpc_url,
        timeout_seconds=settings.bittensor_rpc_timeout_seconds,
        max_retries=settings.bittensor_rpc_max_retries,
    )


def get_cache_service(request: Request) -> CacheService:
    settings: Settings = request.app.state.settings
    return CacheService(request.app.state.redis, settings.redis_default_ttl_seconds)


def _to_validator_response(validator) -> ValidatorResponse:
    metadata = validator.metadata_json
    return ValidatorResponse(
        hotkey=validator.hotkey,
        subnet_id=validator.subnet_id,
        uid=validator.uid,
        display_name=str(metadata.get("display_name", validator.hotkey)),
        reliability_score=int(metadata.get("reliability_score", 0)),
        apy_estimate=float(metadata.get("apy_estimate", 0.0)),
        uptime_percent=float(metadata.get("uptime_percent", 0.0)),
        reward_consistency=float(metadata.get("reward_consistency", 0.0)),
        delegated_stake_rao=int(metadata.get("delegated_stake_rao", 0)),
    )


def _assert_wallet_scope(path_wallet: str, header_wallet: str | None) -> None:
    if header_wallet and header_wallet != path_wallet:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet header does not match requested address",
        )


async def _validator_cache_watermark(request: Request) -> str:
    value = await request.app.state.redis.get(cache_key("validators", "watermark"))
    return value or "0"


@router.get("/validators", response_model=PaginatedResponse[ValidatorResponse])
async def list_validators(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    subnet_id: int | None = None,
    search: str | None = None,
    sort: Annotated[str, Query(pattern="^(score|apy|hotkey)$")] = "score",
    direction: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> PaginatedResponse[ValidatorResponse]:
    cache = get_cache_service(request)
    watermark = await _validator_cache_watermark(request)
    cache_key_parts = (
        watermark,
        str(page),
        str(page_size),
        str(subnet_id),
        search or "",
        sort,
        direction,
    )
    cached = await cache.get_json("validators", *cache_key_parts)
    if cached is not None:
        return PaginatedResponse.model_validate(cached)

    validators, total_items = await portfolio_service.list_validators(
        session,
        page=page,
        page_size=page_size,
        subnet_id=subnet_id,
        search=search,
        sort=sort,
        direction=direction,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    payload = PaginatedResponse(
        data=[_to_validator_response(validator) for validator in validators],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
    await cache.set_json("validators", payload.model_dump(), *cache_key_parts)
    return payload


@router.get("/validators/{hotkey}", response_model=ValidatorResponse)
async def get_validator(
    hotkey: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    subnet_id: int | None = None,
) -> ValidatorResponse:
    validator = await portfolio_service.get_validator(session, hotkey=hotkey, subnet_id=subnet_id)
    if validator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validator not found")
    return _to_validator_response(validator)


@router.post("/wallets/session", response_model=WalletSessionResponse)
async def create_wallet_session(
    payload: WalletSessionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WalletSessionResponse:
    from datetime import UTC, datetime, timedelta

    from app.database.models import WalletSession

    expires_at = datetime.now(UTC) + timedelta(hours=24)
    session.add(
        WalletSession(wallet_address=payload.wallet_address, expires_at=expires_at)
    )
    await session.commit()
    return WalletSessionResponse(
        wallet_address=payload.wallet_address,
        expires_at=expires_at.isoformat(),
    )


@router.get("/wallets/{wallet_address}/staking", response_model=StakingPortfolioResponse)
async def get_wallet_staking(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> StakingPortfolioResponse:
    _assert_wallet_scope(wallet_address, x_wallet_address)
    stakes = await portfolio_service.list_stakes_for_wallet(session, wallet_address)
    subnet_exposure: dict[str, int] = {}
    total_stake_rao = 0
    positions: list[StakePositionResponse] = []
    for stake in stakes:
        total_stake_rao += stake.amount_rao
        subnet_exposure[str(stake.subnet_id)] = (
            subnet_exposure.get(str(stake.subnet_id), 0) + stake.amount_rao
        )
        positions.append(
            StakePositionResponse(
                validator_hotkey=stake.validator_hotkey,
                subnet_id=stake.subnet_id,
                amount_rao=stake.amount_rao,
            )
        )
    return StakingPortfolioResponse(
        wallet_address=wallet_address,
        total_stake_rao=total_stake_rao,
        positions=positions,
        subnet_exposure=subnet_exposure,
    )


@router.get("/wallets/{wallet_address}/rewards/summary", response_model=RewardSummaryResponse)
async def get_reward_summary(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> RewardSummaryResponse:
    _assert_wallet_scope(wallet_address, x_wallet_address)
    summary = await portfolio_service.reward_summary(session, wallet_address)
    return RewardSummaryResponse(wallet_address=wallet_address, **summary)


@router.get("/wallets/{wallet_address}/rewards/history", response_model=list[RewardHistoryPoint])
async def get_reward_history(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: Annotated[int, Query(ge=7, le=90)] = 30,
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> list[RewardHistoryPoint]:
    _assert_wallet_scope(wallet_address, x_wallet_address)
    history = await portfolio_service.reward_history(session, wallet_address, days=days)
    return [
        RewardHistoryPoint(
            captured_at=point.captured_at.isoformat(),
            amount_rao=point.amount_rao,
            subnet_id=point.subnet_id,
            validator_hotkey=point.validator_hotkey,
        )
        for point in history
    ]


@router.post("/ingestion/catalog-sync")
async def run_catalog_sync(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, int]:
    settings: Settings = request.app.state.settings
    client = build_rpc_client(settings, request)
    chain_head = await fetch_chain_head(client)
    result = await sync_validator_catalog(session, chain_head)
    await request.app.state.redis.set(cache_key("validators", "watermark"), str(result.chain_head))
    await invalidate_namespace(request.app.state.redis, "validators")
    return {
        "chain_head": result.chain_head,
        "validators_upserted": result.validators_upserted,
        "subnets_processed": result.subnets_processed,
    }


@router.post("/ingestion/portfolio-sync")
async def run_portfolio_sync(
    payload: WalletSessionRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, int | str]:
    settings: Settings = request.app.state.settings
    client = build_rpc_client(settings, request)
    chain_head = await fetch_chain_head(client)
    result = await sync_wallet_portfolio(session, payload.wallet_address, chain_head)
    return {
        "wallet_address": result.wallet_address,
        "chain_head": result.chain_head,
        "stakes_upserted": result.stakes_upserted,
        "reward_points_written": result.reward_points_written,
    }

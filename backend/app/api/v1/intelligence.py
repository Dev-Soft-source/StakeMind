from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import assert_wallet_scope, build_rpc_client
from app.api.v1.schemas.common import PaginatedResponse, PaginationMeta
from app.api.v1.schemas.intelligence import (
    CompareValidatorsResponse,
    IntelligenceMeta,
    RewardForecastResponse,
    ValidatorIntelligenceResponse,
    ValidatorRankingResponse,
    WalletRiskResponse,
)
from app.cache.redis import cache_key, invalidate_namespace
from app.core.config import Settings
from app.database.session import get_db_session
from app.ingestion.intelligence_recompute import recompute_intelligence
from app.ingestion.mvp_sync import fetch_chain_head
from app.services.intelligence.queries import (
    build_reward_forecast,
    compare_validators,
    get_validator_intelligence,
    get_wallet_risk,
    list_rankings,
)
from app.services.intelligence.scoring import LIMITATIONS
from app.services.cache import CacheService

router = APIRouter(tags=["intelligence"])


def get_intelligence_cache_service(request: Request) -> CacheService:
    settings: Settings = request.app.state.settings
    return CacheService(request.app.state.redis, settings.intelligence_cache_ttl_seconds)


async def _intelligence_cache_watermark(request: Request) -> str:
    value = await request.app.state.redis.get(cache_key("intelligence", "watermark"))
    return value or "0"


def _meta(row) -> IntelligenceMeta:
    return IntelligenceMeta(
        methodology_version=row.methodology_version,
        as_of_block=row.as_of_block,
        computed_at=row.computed_at,
        limitations=LIMITATIONS,
    )


def _to_ranking(row) -> ValidatorRankingResponse:
    return ValidatorRankingResponse(
        hotkey=row.hotkey,
        subnet_id=row.subnet_id,
        composite_score=row.composite_score,
        apy_estimate=row.apy_estimate,
        reward_consistency=row.reward_consistency,
        uptime_percent=row.uptime_percent,
        rank_subnet=row.rank_subnet,
        rank_global=row.rank_global,
        delegation_trend=row.delegation_trend,
        reputation_signal=row.reputation_signal,
        meta=_meta(row),
    )


def _to_detail(row) -> ValidatorIntelligenceResponse:
    return ValidatorIntelligenceResponse(
        **_to_ranking(row).model_dump(),
        inputs=row.inputs_json,
    )


@router.get("/intelligence/validators/compare", response_model=CompareValidatorsResponse)
async def compare_validator_intelligence(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    hotkeys: Annotated[list[str], Query(min_length=2, max_length=3)],
    subnet_id: int | None = None,
) -> CompareValidatorsResponse:
    rows = await compare_validators(session, hotkeys=hotkeys, subnet_id=subnet_id)
    return CompareValidatorsResponse(
        validators=[_to_detail(row) for row in rows],
        limitations=LIMITATIONS,
    )


@router.get("/intelligence/validators/rankings", response_model=PaginatedResponse[ValidatorRankingResponse])
async def get_validator_rankings(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    subnet_id: int | None = None,
    sort: Annotated[str, Query(pattern="^(score|apy|rank)$")] = "score",
    direction: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> PaginatedResponse[ValidatorRankingResponse]:
    cache = get_intelligence_cache_service(request)
    watermark = await _intelligence_cache_watermark(request)
    cache_key_parts = (
        watermark,
        str(page),
        str(page_size),
        str(subnet_id),
        sort,
        direction,
    )
    cached = await cache.get_json("intelligence", "rankings", *cache_key_parts)
    if cached is not None:
        return PaginatedResponse.model_validate(cached)

    rows, total_items = await list_rankings(
        session,
        page=page,
        page_size=page_size,
        subnet_id=subnet_id,
        sort=sort,
        direction=direction,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    payload = PaginatedResponse(
        data=[_to_ranking(row) for row in rows],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
    await cache.set_json("intelligence", payload.model_dump(mode="json"), "rankings", *cache_key_parts)
    return payload


@router.get("/intelligence/validators/{hotkey}", response_model=ValidatorIntelligenceResponse)
async def get_validator_intelligence_detail(
    hotkey: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    subnet_id: int | None = None,
) -> ValidatorIntelligenceResponse:
    row = await get_validator_intelligence(session, hotkey=hotkey, subnet_id=subnet_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intelligence rollup not found")
    return _to_detail(row)


@router.get("/wallets/{wallet_address}/risk", response_model=WalletRiskResponse)
async def get_wallet_risk_profile(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> WalletRiskResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    row = await get_wallet_risk(session, wallet_address)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk rollup not found")
    return WalletRiskResponse(
        wallet_address=row.wallet_address,
        concentration_validator=row.concentration_validator,
        concentration_subnet=row.concentration_subnet,
        hhi_validator=row.hhi_validator,
        hhi_subnet=row.hhi_subnet,
        reward_volatility=row.reward_volatility,
        downtime_risk_proxy=row.downtime_risk_proxy,
        overall_risk_band=row.overall_risk_band,
        inputs=row.inputs_json,
        meta=_meta(row),
    )


@router.get("/wallets/{wallet_address}/rewards/forecast", response_model=RewardForecastResponse)
async def get_wallet_reward_forecast(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: Annotated[int, Query(ge=7, le=90)] = 30,
    horizon_days: Annotated[int, Query(ge=7, le=30)] = 14,
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> RewardForecastResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    payload = await build_reward_forecast(
        session,
        wallet_address=wallet_address,
        days=days,
        horizon_days=horizon_days,
    )
    return RewardForecastResponse.model_validate(payload)


@router.post("/ingestion/intelligence-recompute")
async def run_intelligence_recompute(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, int | bool]:
    settings: Settings = request.app.state.settings
    client = build_rpc_client(settings, request)
    chain_head = await fetch_chain_head(client)
    result = await recompute_intelligence(
        session,
        chain_head,
        window_days=settings.intelligence_recompute_window_days,
    )
    await request.app.state.redis.set(
        cache_key("intelligence", "watermark"),
        str(result.chain_head),
    )
    await invalidate_namespace(request.app.state.redis, "intelligence")
    return {
        "chain_head": result.chain_head,
        "validators_scored": result.validators_scored,
        "wallets_scored": result.wallets_scored,
        "reused_existing": result.reused_existing,
    }

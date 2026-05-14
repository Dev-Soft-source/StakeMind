from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_premium_scoped_wallet
from app.api.v1.schemas.premium import (
    AdvancedScoreRow,
    AdvancedScoresResponse,
    AlertEvaluateResponse,
    AlertEvaluationItem,
    AlertRuleCreate,
    AlertRuleResponse,
    InAppNotificationResponse,
    OptimizationHintsResponse,
    PortfolioRecommendation,
    PriorityRefreshResponse,
    RecommendationsResponse,
    SubnetAnalyticsResponse,
    SubnetExposureRow,
)
from app.cache.redis import invalidate_namespace
from app.database.models import AlertRule
from app.database.session import get_db_session
from app.services import audit as audit_service
from app.services import portfolio as portfolio_service
from app.services.intelligence.queries import get_wallet_risk, list_rankings
from app.services.intelligence.scoring import LIMITATIONS
from app.services.premium.alerts import evaluate_wallet_alert_rules, list_notifications

router = APIRouter(prefix="/premium", tags=["premium"])

PREMIUM_REPORTING_DISCLAIMER = (
    "Recommendations and exports are informational only. StakeMind does not execute transactions, "
    "provide investment advice, or guarantee outcomes. Past and modeled performance are not "
    "indicative of future results."
)


@router.get("/wallets/{wallet_address}/advanced-scores", response_model=AdvancedScoresResponse)
async def premium_advanced_scores(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
    page_size: Annotated[int, Query(ge=1, le=100)] = 40,
) -> AdvancedScoresResponse:
    rows, _ = await list_rankings(
        session, page=1, page_size=min(page_size, 100), subnet_id=None, sort="score", direction="desc"
    )
    data = [
        AdvancedScoreRow(
            hotkey=r.hotkey,
            subnet_id=int(r.subnet_id),
            composite_score=int(r.composite_score),
            optimization_score=round(
                float(r.composite_score) * (0.55 + 0.45 * float(r.reputation_signal)) / 100.0,
                4,
            ),
            reputation_signal=float(r.reputation_signal),
            apy_estimate=float(r.apy_estimate),
        )
        for r in rows
    ]
    return AdvancedScoresResponse(data=data, limitations=list(LIMITATIONS))


@router.get("/wallets/{wallet_address}/optimization-hints", response_model=OptimizationHintsResponse)
async def premium_optimization_hints(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> OptimizationHintsResponse:
    risk = await get_wallet_risk(session, wallet_address)
    hints: list[str] = []
    if risk is None:
        hints.append("No risk rollup yet; run intelligence recompute after portfolio sync.")
    else:
        if risk.concentration_validator > 0.5:
            hints.append("Consider spreading stake across additional validators to reduce single-validator risk.")
        if risk.reward_volatility > 0.35:
            hints.append("Reward volatility is elevated; review subnet mix and reward history windows.")
        if risk.overall_risk_band == "high":
            hints.append("Overall risk band is high; review concentration and downtime proxy signals.")
    if not hints:
        hints.append("No high-priority optimization hints from current rollups.")
    return OptimizationHintsResponse(hints=hints, limitations=list(LIMITATIONS))


@router.get("/wallets/{wallet_address}/subnet-analytics", response_model=SubnetAnalyticsResponse)
async def premium_subnet_analytics(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> SubnetAnalyticsResponse:
    stakes = await portfolio_service.list_stakes_for_wallet(session, wallet_address)
    total = sum(s.amount_rao for s in stakes) or 1
    by_subnet: dict[int, int] = {}
    for s in stakes:
        by_subnet[s.subnet_id] = by_subnet.get(s.subnet_id, 0) + s.amount_rao
    subnets = [
        SubnetExposureRow(
            subnet_id=sid,
            stake_rao=amt,
            share_of_wallet=round(amt / total, 6),
        )
        for sid, amt in sorted(by_subnet.items(), key=lambda x: x[1], reverse=True)
    ]
    return SubnetAnalyticsResponse(
        wallet_address=wallet_address,
        subnets=subnets,
        limitations=list(LIMITATIONS),
    )


@router.get("/wallets/{wallet_address}/recommendations", response_model=RecommendationsResponse)
async def premium_recommendations(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> RecommendationsResponse:
    risk = await get_wallet_risk(session, wallet_address)
    stakes = await portfolio_service.list_stakes_for_wallet(session, wallet_address)
    recs: list[PortfolioRecommendation] = []
    if risk and risk.concentration_validator > 0.55:
        recs.append(
            PortfolioRecommendation(
                title="Reduce concentration",
                detail="Largest validator weight is high relative to the rest of the book; consider incremental redelegation if it fits your policy.",
            )
        )
    if len(stakes) <= 1 and sum(s.amount_rao for s in stakes) > 0:
        recs.append(
            PortfolioRecommendation(
                title="Diversify validators",
                detail="Portfolio shows a single active stake row; adding validators may improve redundancy (not financial advice).",
            )
        )
    if not recs:
        recs.append(
            PortfolioRecommendation(
                title="No urgent actions",
                detail="Current rollups do not surface a premium-only remediation hint beyond standard monitoring.",
            )
        )
    return RecommendationsResponse(
        wallet_address=wallet_address,
        recommendations=recs,
        disclaimer=PREMIUM_REPORTING_DISCLAIMER,
    )


@router.post("/wallets/{wallet_address}/priority-refresh", response_model=PriorityRefreshResponse)
async def premium_priority_refresh(
    wallet_address: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> PriorityRefreshResponse:
    redis = request.app.state.redis
    await invalidate_namespace(redis, "validators")
    await invalidate_namespace(redis, "intelligence")
    await audit_service.record_audit_event(
        session,
        actor_wallet=wallet_address,
        event_type="premium_priority_refresh",
        payload={"namespaces": ["validators", "intelligence"]},
    )
    await session.commit()
    return PriorityRefreshResponse(invalidated_namespaces=["validators", "intelligence"])


@router.get("/wallets/{wallet_address}/export/portfolio.csv")
async def premium_export_portfolio_csv(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
):
    stakes = await portfolio_service.list_stakes_for_wallet(session, wallet_address)

    def rows():
        yield "subnet_id,validator_hotkey,amount_rao\n"
        for s in stakes:
            yield f"{s.subnet_id},{s.validator_hotkey},{s.amount_rao}\n"

    headers = {
        "Content-Disposition": f'attachment; filename="stakemind-portfolio-{wallet_address[:16]}.csv"',
        "X-StakeMind-Disclaimer": PREMIUM_REPORTING_DISCLAIMER[:180],
    }
    return StreamingResponse(rows(), media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/wallets/{wallet_address}/alert-rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> list[AlertRuleResponse]:
    rules = (
        await session.scalars(
            select(AlertRule).where(AlertRule.wallet_address == wallet_address).order_by(AlertRule.created_at.desc())
        )
    ).all()
    return [
        AlertRuleResponse(
            id=r.id,
            wallet_address=r.wallet_address,
            name=r.name,
            rule_type=r.rule_type,
            threshold_json=r.threshold_json,
            channel=r.channel,
            webhook_url=r.webhook_url,
            enabled=r.enabled,
            quiet_hours_start_utc=r.quiet_hours_start_utc,
            quiet_hours_end_utc=r.quiet_hours_end_utc,
        )
        for r in rules
    ]


@router.post("/wallets/{wallet_address}/alert-rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    wallet_address: str,
    body: AlertRuleCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> AlertRuleResponse:
    rule = AlertRule(
        id=uuid4(),
        wallet_address=wallet_address,
        name=body.name,
        rule_type=body.rule_type,
        threshold_json=body.threshold_json,
        channel=body.channel,
        webhook_url=body.webhook_url,
        enabled=body.enabled,
        quiet_hours_start_utc=body.quiet_hours_start_utc,
        quiet_hours_end_utc=body.quiet_hours_end_utc,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return AlertRuleResponse(
        id=rule.id,
        wallet_address=rule.wallet_address,
        name=rule.name,
        rule_type=rule.rule_type,
        threshold_json=rule.threshold_json,
        channel=rule.channel,
        webhook_url=rule.webhook_url,
        enabled=rule.enabled,
        quiet_hours_start_utc=rule.quiet_hours_start_utc,
        quiet_hours_end_utc=rule.quiet_hours_end_utc,
    )


@router.post("/wallets/{wallet_address}/alerts/evaluate", response_model=AlertEvaluateResponse)
async def evaluate_alerts(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> AlertEvaluateResponse:
    results = await evaluate_wallet_alert_rules(session, wallet_address=wallet_address)
    await session.commit()
    return AlertEvaluateResponse(
        results=[
            AlertEvaluationItem(
                rule_id=r.rule_id,
                fired=r.fired,
                skipped_reason=r.skipped_reason,
                channel=r.channel,
            )
            for r in results
        ]
    )


@router.get("/wallets/{wallet_address}/notifications", response_model=list[InAppNotificationResponse])
async def list_in_app_notifications(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(require_premium_scoped_wallet)],
) -> list[InAppNotificationResponse]:
    notes = await list_notifications(session, wallet_address=wallet_address, limit=50)
    return [
        InAppNotificationResponse(
            id=n.id,
            title=n.title,
            body=n.body,
            read_at=n.read_at.isoformat() if n.read_at else None,
            created_at=n.created_at,
        )
        for n in notes
    ]

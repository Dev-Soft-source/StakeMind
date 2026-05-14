"""Smart alerts: rule evaluation, in-app delivery, hourly dedupe, quiet hours."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AlertDeliveryLog, AlertRule, InAppNotification, WalletRiskRollup


def utc_hour_bucket(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H")


def is_within_quiet_hours(
    now: datetime,
    start_hour: int | None,
    end_hour: int | None,
) -> bool:
    if start_hour is None or end_hour is None:
        return False
    hour = now.astimezone(UTC).hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def rule_matches_risk_band(rule: AlertRule, risk: WalletRiskRollup | None) -> bool:
    if risk is None:
        return False
    if rule.rule_type != "risk_band_equals":
        return False
    expected = str(rule.threshold_json.get("band", "")).lower()
    return risk.overall_risk_band.lower() == expected


async def try_insert_delivery_dedupe(
    session: AsyncSession,
    *,
    rule_id: UUID,
    dedupe_key: str,
) -> bool:
    stmt = (
        insert(AlertDeliveryLog)
        .values(id=uuid4(), alert_rule_id=rule_id, dedupe_key=dedupe_key)
        .on_conflict_do_nothing(constraint="uq_alert_delivery_rule_dedupe")
        .returning(AlertDeliveryLog.id)
    )
    result = await session.execute(stmt)
    row_id = result.scalar_one_or_none()
    return row_id is not None


async def create_in_app_notification(
    session: AsyncSession,
    *,
    wallet_address: str,
    title: str,
    body: str,
    alert_rule_id: UUID | None,
) -> InAppNotification:
    note = InAppNotification(
        id=uuid4(),
        wallet_address=wallet_address,
        title=title,
        body=body,
        alert_rule_id=alert_rule_id,
    )
    session.add(note)
    await session.flush()
    return note


@dataclass(frozen=True)
class AlertEvaluationResult:
    rule_id: UUID
    fired: bool
    skipped_reason: str | None
    channel: str


async def evaluate_wallet_alert_rules(
    session: AsyncSession,
    *,
    wallet_address: str,
    now: datetime | None = None,
) -> list[AlertEvaluationResult]:
    now = now or datetime.now(UTC)
    rules = (
        await session.scalars(
            select(AlertRule).where(
                AlertRule.wallet_address == wallet_address,
                AlertRule.enabled.is_(True),
            )
        )
    ).all()
    risk = await session.scalar(
        select(WalletRiskRollup).where(WalletRiskRollup.wallet_address == wallet_address)
    )

    results: list[AlertEvaluationResult] = []
    dedupe_bucket = utc_hour_bucket(now)

    for rule in rules:
        if not rule_matches_risk_band(rule, risk):
            results.append(
                AlertEvaluationResult(rule_id=rule.id, fired=False, skipped_reason="no_match", channel=rule.channel)
            )
            continue

        if is_within_quiet_hours(now, rule.quiet_hours_start_utc, rule.quiet_hours_end_utc):
            results.append(
                AlertEvaluationResult(
                    rule_id=rule.id, fired=False, skipped_reason="quiet_hours", channel=rule.channel
                )
            )
            continue

        dedupe_key = f"{dedupe_bucket}"
        inserted = await try_insert_delivery_dedupe(session, rule_id=rule.id, dedupe_key=dedupe_key)
        if not inserted:
            results.append(
                AlertEvaluationResult(rule_id=rule.id, fired=False, skipped_reason="deduped", channel=rule.channel)
            )
            continue

        if rule.channel == "in_app":
            title = f"Alert: {rule.name}"
            body = (
                f"Risk band is {risk.overall_risk_band if risk else 'unknown'}. "
                "This is informational only; StakeMind does not execute transactions."
            )
            await create_in_app_notification(
                session,
                wallet_address=wallet_address,
                title=title,
                body=body,
                alert_rule_id=rule.id,
            )
        elif rule.channel in ("email", "webhook"):
            # MVP: delivery stub — recorded only via audit from caller if needed
            pass

        results.append(
            AlertEvaluationResult(rule_id=rule.id, fired=True, skipped_reason=None, channel=rule.channel)
        )

    await session.flush()
    return results


async def list_notifications(
    session: AsyncSession,
    *,
    wallet_address: str,
    limit: int = 50,
) -> list[InAppNotification]:
    return (
        await session.scalars(
            select(InAppNotification)
            .where(InAppNotification.wallet_address == wallet_address)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
        )
    ).all()

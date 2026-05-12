from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditEvent


async def record_audit_event(
    session: AsyncSession,
    *,
    actor_wallet: str | None,
    event_type: str,
    payload: dict[str, object],
) -> AuditEvent:
    event = AuditEvent(actor_wallet=actor_wallet, event_type=event_type, payload=payload)
    session.add(event)
    await session.flush()
    return event

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PremiumInviteCode, WalletEntitlement


async def is_wallet_premium(session: AsyncSession, wallet_address: str) -> bool:
    row = await session.get(WalletEntitlement, wallet_address)
    if row is None or row.plan != "premium":
        return False
    if row.valid_until is not None and row.valid_until <= datetime.now(UTC):
        return False
    return True


async def get_wallet_entitlement_view(
    session: AsyncSession,
    wallet_address: str,
) -> dict[str, object]:
    row = await session.get(WalletEntitlement, wallet_address)
    if row is None or row.plan != "premium":
        return {"plan": "free", "source": None, "valid_until": None}
    if row.valid_until is not None and row.valid_until <= datetime.now(UTC):
        return {"plan": "free", "source": None, "valid_until": None}
    return {
        "plan": row.plan,
        "source": row.source,
        "valid_until": row.valid_until.isoformat() if row.valid_until else None,
    }


async def redeem_invite_code(
    session: AsyncSession,
    *,
    wallet_address: str,
    code: str,
) -> WalletEntitlement:
    normalized = code.strip()
    invite = await session.scalar(
        select(PremiumInviteCode).where(PremiumInviteCode.code == normalized).with_for_update()
    )
    if invite is None:
        raise ValueError("invalid_invite_code")
    now = datetime.now(UTC)
    if invite.expires_at is not None and invite.expires_at <= now:
        raise ValueError("invite_expired")
    if invite.redemptions_count >= invite.max_redemptions:
        raise ValueError("invite_exhausted")

    invite.redemptions_count = invite.redemptions_count + 1
    session.add(invite)

    existing = await session.get(WalletEntitlement, wallet_address)
    if existing:
        existing.plan = "premium"
        existing.source = "invite"
        existing.invite_code_id = invite.id
        existing.valid_until = None
        session.add(existing)
        entitlement = existing
    else:
        entitlement = WalletEntitlement(
            wallet_address=wallet_address,
            plan="premium",
            source="invite",
            invite_code_id=invite.id,
            valid_until=None,
        )
        session.add(entitlement)

    await session.flush()
    return entitlement

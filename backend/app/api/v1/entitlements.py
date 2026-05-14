from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import assert_wallet_scope
from app.api.v1.schemas.premium import (
    RedeemInviteRequest,
    RedeemInviteResponse,
    WalletEntitlementResponse,
)
from app.database.session import get_db_session
from app.services import audit as audit_service
from app.services.premium.entitlements import get_wallet_entitlement_view, redeem_invite_code

router = APIRouter(tags=["entitlements"])


@router.get("/wallets/{wallet_address}/entitlements", response_model=WalletEntitlementResponse)
async def read_wallet_entitlements(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> WalletEntitlementResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    view = await get_wallet_entitlement_view(session, wallet_address)
    return WalletEntitlementResponse.model_validate(view)


@router.post("/wallets/{wallet_address}/entitlements/redeem-invite", response_model=RedeemInviteResponse)
async def redeem_wallet_invite(
    wallet_address: str,
    payload: RedeemInviteRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> RedeemInviteResponse:
    assert_wallet_scope(wallet_address, x_wallet_address)
    try:
        await redeem_invite_code(session, wallet_address=wallet_address, code=payload.code)
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_invite_code":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code") from exc
        if code == "invite_expired":
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite code expired") from exc
        if code == "invite_exhausted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite code already used") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from exc

    await audit_service.record_audit_event(
        session,
        actor_wallet=wallet_address,
        event_type="premium_invite_redeemed",
        payload={"code_prefix": payload.code.strip()[:4]},
    )
    await session.commit()
    return RedeemInviteResponse(
        plan="premium",
        source="invite",
        message="Premium unlocked for this wallet. Premium APIs are now available.",
    )

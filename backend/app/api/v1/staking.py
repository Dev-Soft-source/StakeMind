from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import assert_wallet_scope, build_rpc_client
from app.api.v1.schemas.common import PaginatedResponse, PaginationMeta
from app.api.v1.schemas.staking import (
    BuildStakingTransactionRequest,
    StakingSimulationResponse,
    StakingTransactionPreview,
    StakingTransactionResponse,
    SubmitStakingTransactionRequest,
)
from app.core.config import Settings
from app.database.session import get_db_session
from app.services.staking import (
    BuildTransactionInput,
    build_transaction,
    get_transaction,
    list_wallet_transactions,
    resimulate_transaction,
    submit_transaction,
)

router = APIRouter(tags=["staking"])


def _to_simulation(transaction) -> StakingSimulationResponse | None:
    if not transaction.simulation_result:
        return None
    result = transaction.simulation_result
    return StakingSimulationResponse(
        supported=bool(result.get("supported", False)),
        status=str(result.get("status", "skipped")),
        message=str(result.get("message", "")),
        estimated_fee_rao=result.get("estimated_fee_rao"),
        block_number=result.get("block_number"),
    )


def _to_preview(transaction) -> StakingTransactionPreview:
    simulation = transaction.simulation_result or {}
    return StakingTransactionPreview(
        action=transaction.action,
        subnet_id=transaction.subnet_id,
        amount_rao=transaction.amount_rao,
        source_validator_hotkey=transaction.source_validator_hotkey,
        dest_validator_hotkey=transaction.dest_validator_hotkey,
        estimated_fee_rao=simulation.get("estimated_fee_rao"),
    )


def _to_response(transaction) -> StakingTransactionResponse:
    return StakingTransactionResponse(
        id=transaction.id,
        wallet_address=transaction.wallet_address,
        action=transaction.action,
        subnet_id=transaction.subnet_id,
        amount_rao=transaction.amount_rao,
        source_validator_hotkey=transaction.source_validator_hotkey,
        dest_validator_hotkey=transaction.dest_validator_hotkey,
        status=transaction.status,
        unsigned_payload=transaction.unsigned_payload,
        simulation=_to_simulation(transaction),
        tx_hash=transaction.tx_hash,
        failure_reason=transaction.failure_reason,
        expires_at=transaction.expires_at,
        submitted_at=transaction.submitted_at,
        confirmed_at=transaction.confirmed_at,
        preview=_to_preview(transaction),
    )


@router.post("/staking/transactions/build", response_model=StakingTransactionResponse)
async def build_staking_transaction(
    payload: BuildStakingTransactionRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> StakingTransactionResponse:
    assert_wallet_scope(payload.wallet_address, x_wallet_address)
    settings: Settings = request.app.state.settings
    rpc_client = build_rpc_client(settings, request)
    try:
        transaction = await build_transaction(
            session,
            rpc_client,
            settings,
            BuildTransactionInput(
                wallet_address=payload.wallet_address,
                action=payload.action,
                subnet_id=payload.subnet_id,
                amount_rao=payload.amount_rao,
                source_validator_hotkey=payload.source_validator_hotkey,
                dest_validator_hotkey=payload.dest_validator_hotkey,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_response(transaction)


@router.post(
    "/staking/transactions/{transaction_id}/simulate",
    response_model=StakingTransactionResponse,
)
async def simulate_staking_transaction(
    transaction_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StakingTransactionResponse:
    settings: Settings = request.app.state.settings
    rpc_client = build_rpc_client(settings, request)
    transaction = await get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    try:
        transaction = await resimulate_transaction(session, rpc_client, settings, transaction)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_response(transaction)


@router.post(
    "/staking/transactions/{transaction_id}/submit",
    response_model=StakingTransactionResponse,
)
async def submit_staking_transaction(
    transaction_id: UUID,
    payload: SubmitStakingTransactionRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> StakingTransactionResponse:
    settings: Settings = request.app.state.settings
    transaction = await get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    assert_wallet_scope(transaction.wallet_address, x_wallet_address)
    try:
        transaction = await submit_transaction(
            session,
            settings,
            transaction,
            tx_hash=payload.tx_hash,
            signed_extrinsic=payload.signed_extrinsic,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_response(transaction)


@router.get("/staking/transactions/{transaction_id}", response_model=StakingTransactionResponse)
async def get_staking_transaction(
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> StakingTransactionResponse:
    transaction = await get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    assert_wallet_scope(transaction.wallet_address, x_wallet_address)
    return _to_response(transaction)


@router.get(
    "/wallets/{wallet_address}/transactions",
    response_model=PaginatedResponse[StakingTransactionResponse],
)
async def list_wallet_staking_transactions(
    wallet_address: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    x_wallet_address: Annotated[str | None, Header(alias="X-Wallet-Address")] = None,
) -> PaginatedResponse[StakingTransactionResponse]:
    assert_wallet_scope(wallet_address, x_wallet_address)
    transactions, total_items = await list_wallet_transactions(
        session,
        wallet_address,
        page=page,
        page_size=page_size,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse(
        data=[_to_response(transaction) for transaction in transactions],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )

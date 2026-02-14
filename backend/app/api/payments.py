import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, BalancesResponse, SettleRequest
from app.services.payment_service import record_payment, settle_debt
from app.services.settlement_service import calculate_balances

router = APIRouter(tags=["payments"])


@router.post("/api/receipts/{receipt_id}/payments", response_model=PaymentResponse, status_code=201)
async def create_payment(
    receipt_id: uuid.UUID,
    body: PaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await record_payment(db, receipt_id, body.paid_by, body.amount)


@router.get("/api/groups/{group_id}/balances", response_model=BalancesResponse)
async def get_balances(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balances = await calculate_balances(db, group_id)
    return BalancesResponse(balances=balances)


@router.post("/api/groups/{group_id}/settle")
async def settle(
    group_id: uuid.UUID,
    body: SettleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await settle_debt(db, group_id, body.from_user, body.to_user, body.amount)
    return {"status": "settled"}

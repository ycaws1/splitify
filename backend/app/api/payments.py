import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, BalancesResponse, SettleRequest
from app.services.payment_service import record_payment, update_payment, delete_payment, settle_debt, clear_group_settlements
from app.services.settlement_service import calculate_balances

router = APIRouter(tags=["payments"])


@router.get("/api/receipts/{receipt_id}/payments", response_model=list[PaymentResponse])
async def list_payments(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.payment_service import get_receipt_payments
    return await get_receipt_payments(db, receipt_id)


@router.post("/api/receipts/{receipt_id}/payments", response_model=PaymentResponse, status_code=201)
async def create_payment(
    receipt_id: uuid.UUID,
    body: PaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    try:
        return await record_payment(db, receipt_id, body.paid_by, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/payments/{payment_id}", response_model=PaymentResponse)
async def edit_payment(
    payment_id: uuid.UUID,
    body: PaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    try:
        payment = await update_payment(db, payment_id, body.paid_by, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/api/payments/{payment_id}", status_code=204)
async def remove_payment(
    payment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    if not await delete_payment(db, payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")


@router.get("/api/groups/{group_id}/balances", response_model=BalancesResponse)
async def get_balances(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_balances(db, group_id)
    return BalancesResponse(**result)


@router.post("/api/groups/{group_id}/settle")
async def settle(
    group_id: uuid.UUID,
    body: SettleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await settle_debt(db, group_id, body.from_user, body.to_user, body.amount)
    return {"status": "settled"}


@router.delete("/api/groups/{group_id}/reset")
async def reset_group_data(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all receipts, payments, and settlements for a group."""
    from app.services.receipt_service import delete_all_receipts
    receipts_deleted = await delete_all_receipts(db, group_id)
    settlements_deleted = await clear_group_settlements(db, group_id)
    return {"receipts_deleted": receipts_deleted, "settlements_deleted": settlements_deleted}

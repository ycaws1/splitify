import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.receipt import (
    ReceiptCreate, ManualReceiptCreate, ReceiptResponse, ReceiptUpdate, ReceiptListResponse,
    LineItemCreate, LineItemUpdate, LineItemResponse,
)
from app.services.receipt_service import (
    create_receipt, create_manual_receipt, list_receipts, get_receipt, update_receipt, delete_receipt, delete_all_receipts,
    add_line_item, update_line_item, delete_line_item,
)

from app.services.exchange_rate_service import get_exchange_rate
from app.workers.ocr import process_receipt_ocr

router = APIRouter(tags=["receipts"])


@router.get("/api/exchange-rate")
async def fetch_exchange_rate(
    from_currency: str,
    to_currency: str,
    user: User = Depends(get_current_user),
):
    try:
        rate = await get_exchange_rate(from_currency, to_currency)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"rate": rate, "from": from_currency.upper(), "to": to_currency.upper()}


@router.post("/api/groups/{group_id}/receipts", response_model=ReceiptResponse, status_code=201)
async def upload_receipt(
    group_id: uuid.UUID,
    body: ReceiptCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await create_receipt(db, group_id, body.image_url, user, currency=body.currency)
    background_tasks.add_task(process_receipt_ocr, receipt.id, body.currency)
    return receipt


@router.post("/api/groups/{group_id}/receipts/manual", response_model=ReceiptResponse, status_code=201)
async def create_manual(
    group_id: uuid.UUID,
    body: ManualReceiptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await create_manual_receipt(
        db,
        group_id,
        user,
        merchant_name=body.merchant_name,
        currency=body.currency,
        exchange_rate=body.exchange_rate,
        items=[item.model_dump() for item in body.items],
        receipt_date=body.receipt_date,
        tax=body.tax,
        service_charge=body.service_charge,
    )
    return receipt


@router.get("/api/groups/{group_id}/receipts", response_model=list[ReceiptListResponse])
async def list_group_receipts(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_receipts(db, group_id)


@router.get("/api/receipts/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt_detail(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await get_receipt(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.put("/api/receipts/{receipt_id}", response_model=ReceiptResponse)
async def edit_receipt(
    receipt_id: uuid.UUID,
    body: ReceiptUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude={"version"}, exclude_unset=True)
    updated = await update_receipt(db, receipt_id, data, body.version)
    if not updated:
        raise HTTPException(status_code=409, detail="Version conflict, please refresh")
    return updated


@router.delete("/api/receipts/{receipt_id}", status_code=204)
async def remove_receipt(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_receipt(db, receipt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Receipt not found")


@router.delete("/api/groups/{group_id}/receipts", status_code=200)
async def remove_all_receipts(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await delete_all_receipts(db, group_id)
    return {"deleted": count}


@router.post("/api/receipts/{receipt_id}/confirm", response_model=ReceiptResponse)
async def confirm_receipt(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await get_receipt(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    updated = await update_receipt(db, receipt_id, {"status": "confirmed"}, receipt.version)
    if not updated:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated


@router.post("/api/receipts/{receipt_id}/items", response_model=LineItemResponse, status_code=201)
async def create_item(
    receipt_id: uuid.UUID,
    body: LineItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await add_line_item(db, receipt_id, body.description, body.amount, body.quantity)
    if not item:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return item


@router.put("/api/items/{item_id}", response_model=LineItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: LineItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    item = await update_line_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/api/items/{item_id}", status_code=204)
async def delete_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_line_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")

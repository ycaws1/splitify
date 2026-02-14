import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.receipt import (
    ReceiptCreate, ReceiptResponse, ReceiptUpdate, ReceiptListResponse,
)
from app.services.receipt_service import (
    create_receipt, list_receipts, get_receipt, update_receipt,
)

# TODO (Task 8): Import OCR worker once implemented
# from app.workers.ocr import process_receipt_ocr

router = APIRouter(tags=["receipts"])


@router.post("/api/groups/{group_id}/receipts", response_model=ReceiptResponse, status_code=201)
async def upload_receipt(
    group_id: uuid.UUID,
    body: ReceiptCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt = await create_receipt(db, group_id, body.image_url, user)
    # OCR processing will be added in Task 8
    # background_tasks.add_task(process_receipt_ocr, receipt.id)
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

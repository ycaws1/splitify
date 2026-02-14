import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.assignment import BulkAssignRequest, AssignmentResponse
from app.services.assignment_service import bulk_assign, get_assignments

router = APIRouter(tags=["assignments"])


@router.put("/api/receipts/{receipt_id}/assignments", response_model=list[AssignmentResponse])
async def assign_users(
    receipt_id: uuid.UUID,
    body: BulkAssignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await bulk_assign(
        db, receipt_id,
        [a.model_dump() for a in body.assignments],
        body.version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict, please refresh")
    return result


@router.get("/api/receipts/{receipt_id}/assignments", response_model=list[AssignmentResponse])
async def get_receipt_assignments(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_assignments(db, receipt_id)

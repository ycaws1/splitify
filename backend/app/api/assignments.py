import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.assignment import BulkAssignRequest, AssignmentResponse, ToggleAssignmentRequest
from app.services.assignment_service import bulk_assign, get_assignments, toggle_assignment, assign_all_to_all

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


@router.post("/api/receipts/{receipt_id}/assignments/assign-all", response_model=list[AssignmentResponse])
async def assign_all_items(
    receipt_id: uuid.UUID,
    # Optional version check if needed, but for "force all" often we just want to apply it
    # We can accept a body with version if we want strictness, or just Query param
    # For simplicity let's assume last-write-wins if version not provided, but good to have.
    # Let's use a simple body model or just ignore version for this button for now to avoid UI complexity,
    # as "Assign All" is a heavy override action.
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await assign_all_to_all(db, receipt_id, expected_version=None)
    if result is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return result


@router.post("/api/receipts/{receipt_id}/assignments/toggle", response_model=dict)
async def toggle_user_assignment(
    receipt_id: uuid.UUID,
    body: ToggleAssignmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fast toggle endpoint for optimistic UI updates. Only modifies one assignment."""
    print(f"DEBUG: toggle assignment receipt_id={receipt_id}, line_item_id={body.line_item_id}, user_id={body.user_id}, expected_version={body.version}")
    result = await toggle_assignment(
        db, receipt_id, body.line_item_id, body.user_id, body.version
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

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse, GroupListResponse, InviteResponse
from app.services.group_service import create_group, list_user_groups, get_group, update_group, join_group_by_code, delete_group

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("", response_model=GroupResponse, status_code=201)
async def create(
    body: GroupCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await create_group(db, body.name, user, base_currency=body.base_currency)
    return group


@router.get("", response_model=list[GroupListResponse])
async def list_groups(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_groups(db, user.id)


@router.get("/{group_id}", response_model=GroupResponse)
async def get(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.put("/{group_id}", response_model=GroupResponse)
async def update(
    group_id: uuid.UUID,
    body: GroupUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await update_group(db, group_id, body.base_currency)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/{group_id}", status_code=204)
async def delete(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_group(db, group_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{group_id}/invite", response_model=InviteResponse)
async def invite(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return InviteResponse(
        invite_code=group.invite_code,
        invite_url=f"/join/{group.invite_code}",
    )


@router.post("/join/{code}", response_model=GroupResponse)
async def join(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group = await join_group_by_code(db, code, user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return group

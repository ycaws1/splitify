import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.group import GroupCreate, GroupResponse, GroupListResponse, InviteResponse
from app.services.group_service import create_group, list_user_groups, get_group, join_group_by_code

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("", response_model=GroupResponse, status_code=201)
async def create(
    body: GroupCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await create_group(db, body.name, user)
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

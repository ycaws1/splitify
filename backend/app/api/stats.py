import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.stats_service import get_group_stats

router = APIRouter(tags=["stats"])


@router.get("/api/groups/{group_id}/stats")
async def group_stats(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_group_stats(db, group_id)

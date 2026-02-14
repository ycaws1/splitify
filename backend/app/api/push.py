from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


@router.post("/subscribe")
async def subscribe(
    body: PushSubscription,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.push_subscription = body.model_dump()
    await db.commit()
    return {"status": "subscribed"}


@router.delete("/subscribe")
async def unsubscribe(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.push_subscription = None
    await db.commit()
    return {"status": "unsubscribed"}

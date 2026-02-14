import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthCallbackRequest(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None = None


@router.post("/callback")
async def auth_callback(
    body: AuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Sync Supabase user to local DB after signup/login."""
    user_id = uuid.UUID(body.id)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user:
        user.display_name = body.display_name
        if body.avatar_url:
            user.avatar_url = body.avatar_url
    else:
        user = User(
            id=user_id,
            email=body.email,
            display_name=body.display_name,
            avatar_url=body.avatar_url,
        )
        db.add(user)

    await db.commit()
    return {"status": "ok"}

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthCallbackRequest(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str


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


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


@router.patch("/me")
async def update_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.display_name = body.display_name
    await db.commit()
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }

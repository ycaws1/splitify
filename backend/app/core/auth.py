import uuid

import httpx
import jwt as pyjwt
from jwt import PyJWK
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()

_jwks_cache: list | None = None


async def _get_jwks() -> list:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        _jwks_cache = [PyJWK(k) for k in keys]
        return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        header = pyjwt.get_unverified_header(token)
        kid = header.get("kid")

        key = None
        for k in jwks:
            if k.key_id == kid:
                key = k
                break
        if key is None:
            raise pyjwt.InvalidTokenError("No matching key found")

        payload = pyjwt.decode(
            token,
            key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user

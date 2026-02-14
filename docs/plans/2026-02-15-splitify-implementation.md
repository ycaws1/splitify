# Splitify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a bill-splitting PWA where groups upload receipts, AI extracts line items, users assign responsibilities, and the app calculates balances with push reminders.

**Architecture:** Next.js 15 frontend (Vercel) talks to FastAPI backend (Render). Supabase provides auth, Postgres DB, storage, and realtime. Claude vision API handles receipt OCR. All business logic lives in FastAPI.

**Tech Stack:** Next.js 15 / TypeScript / Tailwind 4 / FastAPI / SQLAlchemy 2.0 async / Supabase / Claude API / Web Push

---

## Phase 1: Project Scaffolding

### Task 1: Initialize Backend Project

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/{api,models,schemas,services,core,workers}
touch backend/app/__init__.py backend/app/api/__init__.py backend/app/models/__init__.py
touch backend/app/schemas/__init__.py backend/app/services/__init__.py
touch backend/app/core/__init__.py backend/app/workers/__init__.py
```

**Step 2: Write requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
pydantic==2.10.4
pydantic-settings==2.7.1
python-multipart==0.0.20
httpx==0.28.1
anthropic==0.43.0
pywebpush==2.0.1
py-vapid==1.9.2
python-jose[cryptography]==3.3.0
supabase==2.11.0
pytest==8.3.4
pytest-asyncio==0.25.0
```

**Step 3: Write config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str
    anthropic_api_key: str
    vapid_private_key: str
    vapid_public_key: str
    vapid_claims_email: str


settings = Settings()
```

**Step 4: Write main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Splitify API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 5: Create backend .env template**

Create `backend/.env.example`:
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
DATABASE_URL=
ANTHROPIC_API_KEY=
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_EMAIL=
```

**Step 6: Verify backend starts**

Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
Expected: Server starts on port 8000, `GET /api/health` returns `{"status": "ok"}`

**Step 7: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI backend with config and health endpoint"
```

---

### Task 2: Initialize Frontend Project

**Step 1: Create Next.js app**

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

**Step 2: Install additional dependencies**

```bash
cd frontend && npm install @supabase/supabase-js @supabase/ssr react-hook-form @hookform/resolvers zod qrcode.react next-pwa
cd frontend && npm install -D @types/qrcode.react
```

**Step 3: Create Supabase client utility**

Create `frontend/src/lib/supabase/client.ts`:
```typescript
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

**Step 4: Create API client utility**

Create `frontend/src/lib/api.ts`:
```typescript
import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(session?.access_token && {
        Authorization: `Bearer ${session.access_token}`,
      }),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }

  return res.json();
}
```

**Step 5: Create .env.local template**

Create `frontend/.env.local.example`:
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_VAPID_PUBLIC_KEY=
```

**Step 6: Verify frontend starts**

Run: `cd frontend && npm run dev`
Expected: Next.js dev server on port 3000

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with Supabase client and API utility"
```

---

### Task 3: Set Up Database and Alembic Migrations

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

**Step 1: Write database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

**Step 2: Initialize Alembic**

```bash
cd backend && alembic init alembic
```

**Step 3: Update alembic/env.py to use async engine and import models**

Replace the generated `env.py` with async-compatible version that imports `Base.metadata` and uses `run_async_migrations`.

Key changes:
- `from app.core.database import Base`
- `from app.models import *`  (to register all models)
- `target_metadata = Base.metadata`
- Use `connectable = create_async_engine(settings.database_url)` with `async with connectable.connect()` pattern

**Step 4: Update alembic.ini**

Set `sqlalchemy.url` to empty (we'll use the env-based URL from config).

**Step 5: Commit**

```bash
git add backend/app/core/database.py backend/alembic/ backend/alembic.ini
git commit -m "feat: set up async SQLAlchemy engine and Alembic migrations"
```

---

## Phase 2: Database Models

### Task 4: Create All SQLAlchemy Models

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/group.py`
- Create: `backend/app/models/receipt.py`
- Create: `backend/app/models/payment.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write user model**

`backend/app/models/user.py`:
```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    push_subscription: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

**Step 2: Write group models**

`backend/app/models/group.py`:
```python
import uuid
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class GroupRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False,
        default=lambda: ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", lazy="selectin")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[GroupRole] = mapped_column(SAEnum(GroupRole), nullable=False, default=GroupRole.member)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    group: Mapped["Group"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(lazy="selectin")
```

**Step 3: Write receipt and line item models**

`backend/app/models/receipt.py`:
```python
import uuid
import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Date, DateTime, Integer, Numeric, ForeignKey,
    Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReceiptStatus(str, enum.Enum):
    processing = "processing"
    extracted = "extracted"
    confirmed = "confirmed"


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MYR")
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    service_charge: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[ReceiptStatus] = mapped_column(
        SAEnum(ReceiptStatus), nullable=False, default=ReceiptStatus.processing
    )
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    line_items: Mapped[list["LineItem"]] = relationship(back_populates="receipt", lazy="selectin", order_by="LineItem.sort_order")
    uploader: Mapped["User"] = relationship(lazy="selectin")


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("receipts.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    receipt: Mapped["Receipt"] = relationship(back_populates="line_items")
    assignments: Mapped[list["LineItemAssignment"]] = relationship(back_populates="line_item", lazy="selectin")


class LineItemAssignment(Base):
    __tablename__ = "line_item_assignments"
    __table_args__ = (UniqueConstraint("line_item_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("line_items.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    line_item: Mapped["LineItem"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(lazy="selectin")
```

**Step 4: Write payment and settlement models**

`backend/app/models/payment.py`:
```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("receipts.id"), nullable=False)
    paid_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    payer: Mapped["User"] = relationship(lazy="selectin")


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    from_user: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    to_user: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    debtor: Mapped["User"] = relationship(foreign_keys=[from_user], lazy="selectin")
    creditor: Mapped["User"] = relationship(foreign_keys=[to_user], lazy="selectin")
```

**Step 5: Update models/__init__.py**

```python
from app.models.user import User
from app.models.group import Group, GroupMember, GroupRole
from app.models.receipt import Receipt, LineItem, LineItemAssignment, ReceiptStatus
from app.models.payment import Payment, Settlement

__all__ = [
    "User", "Group", "GroupMember", "GroupRole",
    "Receipt", "LineItem", "LineItemAssignment", "ReceiptStatus",
    "Payment", "Settlement",
]
```

**Step 6: Generate initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```

**Step 7: Commit**

```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat: add all SQLAlchemy models and initial migration"
```

---

## Phase 3: Auth Middleware

### Task 5: Supabase JWT Auth Dependency

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/tests/test_auth.py`

**Step 1: Write the failing test**

`backend/tests/test_auth.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_no_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_no_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/groups")
    assert res.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: Second test fails (no /api/groups route yet, or returns 404 not 401)

**Step 3: Write auth dependency**

`backend/app/core/auth.py`:
```python
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
```

**Step 4: Write auth callback endpoint**

`backend/app/api/auth.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

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
    import uuid

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
```

**Step 5: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.api.auth import router as auth_router
app.include_router(auth_router)
```

**Step 6: Run tests and verify**

Run: `cd backend && pytest tests/test_auth.py -v`

**Step 7: Commit**

```bash
git add backend/app/core/auth.py backend/app/api/auth.py backend/tests/test_auth.py backend/app/main.py
git commit -m "feat: add Supabase JWT auth middleware and auth callback endpoint"
```

---

## Phase 4: Groups API

### Task 6: Groups CRUD + Invite System

**Files:**
- Create: `backend/app/schemas/group.py`
- Create: `backend/app/services/group_service.py`
- Create: `backend/app/api/groups.py`
- Create: `backend/tests/test_groups.py`

**Step 1: Write Pydantic schemas**

`backend/app/schemas/group.py`:
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    name: str


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    role: str
    display_name: str | None = None
    joined_at: datetime


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    invite_code: str
    created_by: uuid.UUID
    created_at: datetime
    members: list[MemberResponse] = []


class GroupListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    created_at: datetime


class InviteResponse(BaseModel):
    invite_code: str
    invite_url: str
```

**Step 2: Write group service**

`backend/app/services/group_service.py`:
```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupMember, GroupRole
from app.models.user import User


async def create_group(db: AsyncSession, name: str, user: User) -> Group:
    group = Group(name=name, created_by=user.id)
    db.add(group)
    await db.flush()

    member = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.owner)
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group


async def list_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list(result.scalars().all())


async def get_group(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


async def join_group_by_code(db: AsyncSession, invite_code: str, user: User) -> Group:
    result = await db.execute(select(Group).where(Group.invite_code == invite_code))
    group = result.scalar_one_or_none()
    if not group:
        raise ValueError("Invalid invite code")

    existing = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return group  # already a member

    member = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.member)
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group
```

**Step 3: Write route handlers**

`backend/app/api/groups.py`:
```python
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
```

**Step 4: Register router in main.py**

Add: `from app.api.groups import router as groups_router` and `app.include_router(groups_router)`

**Step 5: Commit**

```bash
git add backend/app/schemas/group.py backend/app/services/group_service.py backend/app/api/groups.py backend/app/main.py
git commit -m "feat: add groups CRUD API with invite code join system"
```

---

## Phase 5: Receipt Upload + OCR

### Task 7: Receipt Upload Endpoint

**Files:**
- Create: `backend/app/schemas/receipt.py`
- Create: `backend/app/services/receipt_service.py`
- Create: `backend/app/api/receipts.py`

**Step 1: Write receipt schemas**

`backend/app/schemas/receipt.py`:
```python
import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ReceiptCreate(BaseModel):
    image_url: str


class LineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    sort_order: int


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    group_id: uuid.UUID
    uploaded_by: uuid.UUID
    image_url: str
    merchant_name: str | None
    receipt_date: date | None
    currency: str
    subtotal: Decimal | None
    tax: Decimal | None
    service_charge: Decimal | None
    total: Decimal | None
    status: str
    version: int
    created_at: datetime
    line_items: list[LineItemResponse] = []


class ReceiptUpdate(BaseModel):
    merchant_name: str | None = None
    receipt_date: date | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    service_charge: Decimal | None = None
    total: Decimal | None = None
    version: int  # required for optimistic locking


class ReceiptListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    merchant_name: str | None
    total: Decimal | None
    status: str
    created_at: datetime
```

**Step 2: Write receipt service**

`backend/app/services/receipt_service.py`:
```python
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User


async def create_receipt(
    db: AsyncSession, group_id: uuid.UUID, image_url: str, user: User
) -> Receipt:
    receipt = Receipt(
        group_id=group_id,
        uploaded_by=user.id,
        image_url=image_url,
        status=ReceiptStatus.processing,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return receipt


async def list_receipts(db: AsyncSession, group_id: uuid.UUID) -> list[Receipt]:
    result = await db.execute(
        select(Receipt)
        .where(Receipt.group_id == group_id)
        .order_by(Receipt.created_at.desc())
    )
    return list(result.scalars().all())


async def get_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> Receipt | None:
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    return result.scalar_one_or_none()


async def update_receipt(
    db: AsyncSession, receipt_id: uuid.UUID, data: dict, expected_version: int
) -> Receipt | None:
    """Update receipt with optimistic locking. Returns None if version conflict."""
    result = await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.version == expected_version)
        .values(**data, version=expected_version + 1)
        .returning(Receipt)
    )
    await db.commit()
    row = result.scalar_one_or_none()
    return row
```

**Step 3: Write route handlers**

`backend/app/api/receipts.py`:
```python
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
from app.workers.ocr import process_receipt_ocr

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
    background_tasks.add_task(process_receipt_ocr, receipt.id)
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
```

**Step 4: Register router in main.py**

Add: `from app.api.receipts import router as receipts_router` and `app.include_router(receipts_router)`

**Step 5: Commit**

```bash
git add backend/app/schemas/receipt.py backend/app/services/receipt_service.py backend/app/api/receipts.py backend/app/main.py
git commit -m "feat: add receipt upload, list, edit, confirm endpoints with optimistic locking"
```

---

### Task 8: Claude Vision OCR Worker

**Files:**
- Create: `backend/app/workers/ocr.py`

**Step 1: Write OCR worker**

`backend/app/workers/ocr.py`:
```python
import json
import uuid
import anthropic

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.receipt import Receipt, LineItem, ReceiptStatus


EXTRACTION_PROMPT = """Analyze this receipt/invoice image. Extract all information into this exact JSON structure:

{
  "merchant_name": "string",
  "receipt_date": "YYYY-MM-DD",
  "currency": "3-letter code e.g. MYR, USD",
  "line_items": [
    {
      "description": "item name",
      "quantity": 1.0,
      "unit_price": 0.00,
      "amount": 0.00
    }
  ],
  "subtotal": 0.00,
  "tax": 0.00,
  "service_charge": 0.00,
  "total": 0.00
}

Rules:
- Return ONLY valid JSON, no markdown or explanation.
- If a field is not visible, use null.
- amount = quantity * unit_price for each line item.
- Use the currency shown on the receipt, default to MYR if unclear.
"""


async def process_receipt_ocr(receipt_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
        receipt = result.scalar_one_or_none()
        if not receipt:
            return

        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "url", "url": receipt.image_url},
                            },
                            {"type": "text", "text": EXTRACTION_PROMPT},
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text
            data = json.loads(raw_text)

            receipt.merchant_name = data.get("merchant_name")
            receipt.receipt_date = data.get("receipt_date")
            receipt.currency = data.get("currency", "MYR")
            receipt.subtotal = data.get("subtotal")
            receipt.tax = data.get("tax")
            receipt.service_charge = data.get("service_charge")
            receipt.total = data.get("total")
            receipt.raw_llm_response = data
            receipt.status = ReceiptStatus.extracted

            for i, item in enumerate(data.get("line_items", [])):
                line_item = LineItem(
                    receipt_id=receipt.id,
                    description=item["description"],
                    quantity=item.get("quantity", 1),
                    unit_price=item["unit_price"],
                    amount=item["amount"],
                    sort_order=i,
                )
                db.add(line_item)

            await db.commit()

        except Exception:
            receipt.status = ReceiptStatus.processing  # stays in processing on failure
            await db.commit()
```

**Step 2: Commit**

```bash
git add backend/app/workers/ocr.py
git commit -m "feat: add Claude vision OCR worker for receipt extraction"
```

---

## Phase 6: Assignments API

### Task 9: Line Item Assignment Endpoints

**Files:**
- Create: `backend/app/schemas/assignment.py`
- Create: `backend/app/services/assignment_service.py`
- Create: `backend/app/api/assignments.py`

**Step 1: Write assignment schemas**

`backend/app/schemas/assignment.py`:
```python
import uuid
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class AssignmentItem(BaseModel):
    line_item_id: uuid.UUID
    user_ids: list[uuid.UUID]


class BulkAssignRequest(BaseModel):
    assignments: list[AssignmentItem]
    version: int  # receipt version for optimistic locking


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_item_id: uuid.UUID
    user_id: uuid.UUID
    share_amount: Decimal
```

**Step 2: Write assignment service**

`backend/app/services/assignment_service.py`:
```python
import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment


async def bulk_assign(
    db: AsyncSession,
    receipt_id: uuid.UUID,
    assignments: list[dict],
    expected_version: int,
) -> list[LineItemAssignment]:
    """
    Replace all assignments for the given receipt.
    Each assignment: {line_item_id, user_ids}
    Splits each line item amount equally among assigned users.
    Uses optimistic locking on receipt version.
    """
    # Version check
    result = await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.version == expected_version)
        .values(version=expected_version + 1)
        .returning(Receipt.id)
    )
    if not result.scalar_one_or_none():
        return None  # version conflict

    # Delete existing assignments for this receipt's line items
    line_item_ids = [a["line_item_id"] for a in assignments]
    await db.execute(
        delete(LineItemAssignment).where(
            LineItemAssignment.line_item_id.in_(line_item_ids)
        )
    )

    # Fetch line items to get amounts
    result = await db.execute(
        select(LineItem).where(LineItem.receipt_id == receipt_id)
    )
    line_items_map = {li.id: li for li in result.scalars().all()}

    new_assignments = []
    for a in assignments:
        li = line_items_map.get(a["line_item_id"])
        if not li or not a["user_ids"]:
            continue

        num_users = len(a["user_ids"])
        share = (li.amount / Decimal(num_users)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        for user_id in a["user_ids"]:
            assignment = LineItemAssignment(
                line_item_id=a["line_item_id"],
                user_id=user_id,
                share_amount=share,
            )
            db.add(assignment)
            new_assignments.append(assignment)

    await db.commit()
    return new_assignments


async def get_assignments(db: AsyncSession, receipt_id: uuid.UUID) -> list[LineItemAssignment]:
    result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id == receipt_id)
    )
    return list(result.scalars().all())
```

**Step 3: Write route handlers**

`backend/app/api/assignments.py`:
```python
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
```

**Step 4: Register router in main.py**

Add: `from app.api.assignments import router as assignments_router` and `app.include_router(assignments_router)`

**Step 5: Commit**

```bash
git add backend/app/schemas/assignment.py backend/app/services/assignment_service.py backend/app/api/assignments.py backend/app/main.py
git commit -m "feat: add line item assignment endpoints with equal split and optimistic locking"
```

---

## Phase 7: Payments, Settlements & Balances

### Task 10: Payment Recording + Balance Calculation

**Files:**
- Create: `backend/app/schemas/payment.py`
- Create: `backend/app/services/payment_service.py`
- Create: `backend/app/services/settlement_service.py`
- Create: `backend/app/api/payments.py`

**Step 1: Write payment schemas**

`backend/app/schemas/payment.py`:
```python
import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    paid_by: uuid.UUID
    amount: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    receipt_id: uuid.UUID
    paid_by: uuid.UUID
    amount: Decimal
    created_at: datetime


class BalanceEntry(BaseModel):
    from_user_id: uuid.UUID
    from_user_name: str
    to_user_id: uuid.UUID
    to_user_name: str
    amount: Decimal


class BalancesResponse(BaseModel):
    balances: list[BalanceEntry]


class SettleRequest(BaseModel):
    from_user: uuid.UUID
    to_user: uuid.UUID
    amount: Decimal
```

**Step 2: Write settlement service (debt simplification)**

`backend/app/services/settlement_service.py`:
```python
import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User


async def calculate_balances(db: AsyncSession, group_id: uuid.UUID) -> list[dict]:
    """
    Calculate net balances for a group.
    Returns simplified list of {from_user, to_user, amount} debts.
    """
    # Get all receipts in the group
    receipts_result = await db.execute(
        select(Receipt).where(Receipt.group_id == group_id)
    )
    receipts = receipts_result.scalars().all()
    receipt_ids = [r.id for r in receipts]

    if not receipt_ids:
        return []

    # Get all assignments (what each user owes)
    assignments_result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id.in_(receipt_ids))
    )
    assignments = assignments_result.scalars().all()

    # Get all payments (what each user paid)
    payments_result = await db.execute(
        select(Payment).where(Payment.receipt_id.in_(receipt_ids))
    )
    payments = payments_result.scalars().all()

    # Get settled amounts
    settlements_result = await db.execute(
        select(Settlement).where(
            Settlement.group_id == group_id,
            Settlement.is_settled == True,
        )
    )
    settlements = settlements_result.scalars().all()

    # Calculate net: positive = owes money, negative = is owed
    net = defaultdict(Decimal)

    for a in assignments:
        net[a.user_id] += a.share_amount  # user owes this much

    for p in payments:
        net[p.paid_by] -= p.amount  # user paid this much

    for s in settlements:
        net[s.from_user] -= s.amount  # settled debt reduces what they owe
        net[s.to_user] += s.amount  # and reduces what they're owed

    # Simplify debts using greedy algorithm
    debtors = []  # (user_id, amount they owe)
    creditors = []  # (user_id, amount they're owed)

    for user_id, amount in net.items():
        if amount > 0:
            debtors.append([user_id, amount])
        elif amount < 0:
            creditors.append([user_id, -amount])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    # Fetch user names
    all_user_ids = list(net.keys())
    users_result = await db.execute(select(User).where(User.id.in_(all_user_ids)))
    users_map = {u.id: u.display_name for u in users_result.scalars().all()}

    result = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount = debtors[i]
        creditor_id, credit_amount = creditors[j]

        transfer = min(debt_amount, credit_amount)
        if transfer > Decimal("0.01"):
            result.append({
                "from_user_id": debtor_id,
                "from_user_name": users_map.get(debtor_id, "Unknown"),
                "to_user_id": creditor_id,
                "to_user_name": users_map.get(creditor_id, "Unknown"),
                "amount": transfer.quantize(Decimal("0.01")),
            })

        debtors[i][1] -= transfer
        creditors[j][1] -= transfer

        if debtors[i][1] <= Decimal("0.01"):
            i += 1
        if creditors[j][1] <= Decimal("0.01"):
            j += 1

    return result
```

**Step 3: Write payment service**

`backend/app/services/payment_service.py`:
```python
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, Settlement


async def record_payment(
    db: AsyncSession, receipt_id: uuid.UUID, paid_by: uuid.UUID, amount: Decimal
) -> Payment:
    payment = Payment(receipt_id=receipt_id, paid_by=paid_by, amount=amount)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def settle_debt(
    db: AsyncSession, group_id: uuid.UUID, from_user: uuid.UUID, to_user: uuid.UUID, amount: Decimal
) -> Settlement:
    settlement = Settlement(
        group_id=group_id,
        from_user=from_user,
        to_user=to_user,
        amount=amount,
        is_settled=True,
        settled_at=datetime.now(timezone.utc),
    )
    db.add(settlement)
    await db.commit()
    await db.refresh(settlement)
    return settlement
```

**Step 4: Write route handlers**

`backend/app/api/payments.py`:
```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, BalancesResponse, SettleRequest
from app.services.payment_service import record_payment, settle_debt
from app.services.settlement_service import calculate_balances

router = APIRouter(tags=["payments"])


@router.post("/api/receipts/{receipt_id}/payments", response_model=PaymentResponse, status_code=201)
async def create_payment(
    receipt_id: uuid.UUID,
    body: PaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await record_payment(db, receipt_id, body.paid_by, body.amount)


@router.get("/api/groups/{group_id}/balances", response_model=BalancesResponse)
async def get_balances(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balances = await calculate_balances(db, group_id)
    return BalancesResponse(balances=balances)


@router.post("/api/groups/{group_id}/settle")
async def settle(
    group_id: uuid.UUID,
    body: SettleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await settle_debt(db, group_id, body.from_user, body.to_user, body.amount)
    return {"status": "settled"}
```

**Step 5: Register router in main.py**

Add: `from app.api.payments import router as payments_router` and `app.include_router(payments_router)`

**Step 6: Commit**

```bash
git add backend/app/schemas/payment.py backend/app/services/ backend/app/api/payments.py backend/app/main.py
git commit -m "feat: add payments, balance calculation with debt simplification, and settlement endpoints"
```

---

## Phase 8: Statistics API

### Task 11: Group Statistics Endpoint

**Files:**
- Create: `backend/app/services/stats_service.py`
- Create: `backend/app/api/stats.py`

**Step 1: Write stats service**

`backend/app/services/stats_service.py`:
```python
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment
from app.models.user import User


class Period(str, Enum):
    day = "1d"
    month = "1mo"
    year = "1yr"


def get_period_start(period: Period) -> datetime:
    now = datetime.now(timezone.utc)
    if period == Period.day:
        return now - timedelta(days=1)
    elif period == Period.month:
        return now - timedelta(days=30)
    else:
        return now - timedelta(days=365)


async def get_group_stats(db: AsyncSession, group_id: uuid.UUID, period: Period) -> dict:
    since = get_period_start(period)

    # Total spending
    total_result = await db.execute(
        select(func.sum(Receipt.total))
        .where(Receipt.group_id == group_id, Receipt.created_at >= since)
    )
    total_spending = total_result.scalar() or Decimal("0")

    # Receipt count
    count_result = await db.execute(
        select(func.count(Receipt.id))
        .where(Receipt.group_id == group_id, Receipt.created_at >= since)
    )
    receipt_count = count_result.scalar() or 0

    # Spending per user
    receipts_result = await db.execute(
        select(Receipt.id).where(
            Receipt.group_id == group_id, Receipt.created_at >= since
        )
    )
    receipt_ids = [r for r in receipts_result.scalars().all()]

    per_user = defaultdict(Decimal)
    if receipt_ids:
        assignments_result = await db.execute(
            select(LineItemAssignment.user_id, func.sum(LineItemAssignment.share_amount))
            .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
            .where(LineItem.receipt_id.in_(receipt_ids))
            .group_by(LineItemAssignment.user_id)
        )
        for user_id, amount in assignments_result.all():
            per_user[user_id] = amount

    # Fetch user names
    user_ids = list(per_user.keys())
    users_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u.display_name for u in users_result.scalars().all()}

    spending_by_user = [
        {"user_id": str(uid), "display_name": users_map.get(uid, "Unknown"), "amount": str(amt)}
        for uid, amt in per_user.items()
    ]

    return {
        "period": period.value,
        "total_spending": str(total_spending),
        "receipt_count": receipt_count,
        "spending_by_user": spending_by_user,
    }
```

**Step 2: Write route handler**

`backend/app/api/stats.py`:
```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.stats_service import get_group_stats, Period

router = APIRouter(tags=["stats"])


@router.get("/api/groups/{group_id}/stats")
async def group_stats(
    group_id: uuid.UUID,
    period: Period = Query(default=Period.month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_group_stats(db, group_id, period)
```

**Step 3: Register router in main.py**

Add: `from app.api.stats import router as stats_router` and `app.include_router(stats_router)`

**Step 4: Commit**

```bash
git add backend/app/services/stats_service.py backend/app/api/stats.py backend/app/main.py
git commit -m "feat: add group statistics endpoint with period filtering"
```

---

## Phase 9: Web Push Notifications

### Task 12: Push Subscription + Reminder Worker

**Files:**
- Create: `backend/app/api/push.py`
- Create: `backend/app/workers/reminders.py`

**Step 1: Write push subscription endpoint**

`backend/app/api/push.py`:
```python
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
```

**Step 2: Write reminder worker**

`backend/app/workers/reminders.py`:
```python
import json
from datetime import datetime, timedelta, timezone

from pywebpush import webpush, WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.payment import Settlement
from app.models.user import User
from app.models.group import Group


async def send_overdue_reminders() -> None:
    """Send push notifications for debts older than 2 weeks."""
    async with async_session_factory() as db:
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=2)

        result = await db.execute(
            select(Settlement)
            .where(
                Settlement.is_settled == False,
                Settlement.created_at <= two_weeks_ago,
            )
        )
        overdue = result.scalars().all()

        for settlement in overdue:
            # Get debtor's push subscription
            user_result = await db.execute(
                select(User).where(User.id == settlement.from_user)
            )
            debtor = user_result.scalar_one_or_none()
            if not debtor or not debtor.push_subscription:
                continue

            # Get creditor name
            creditor_result = await db.execute(
                select(User).where(User.id == settlement.to_user)
            )
            creditor = creditor_result.scalar_one_or_none()

            # Get group name
            group_result = await db.execute(
                select(Group).where(Group.id == settlement.group_id)
            )
            group = group_result.scalar_one_or_none()

            payload = json.dumps({
                "title": "Splitify Reminder",
                "body": f"You still owe {creditor.display_name if creditor else 'someone'} "
                        f"${settlement.amount} from {group.name if group else 'a group'}. Settle up!",
                "url": f"/groups/{settlement.group_id}",
            })

            try:
                webpush(
                    subscription_info=debtor.push_subscription,
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": f"mailto:{settings.vapid_claims_email}"},
                )
            except WebPushException:
                pass  # subscription may be expired
```

**Step 3: Add startup scheduler to main.py**

Add to `backend/app/main.py`:
```python
import asyncio
from contextlib import asynccontextmanager
from app.workers.reminders import send_overdue_reminders


async def reminder_loop():
    while True:
        await send_overdue_reminders()
        await asyncio.sleep(86400)  # run daily


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()


# Update: app = FastAPI(title="Splitify API", version="0.1.0", lifespan=lifespan)
```

**Step 4: Register push router in main.py**

Add: `from app.api.push import router as push_router` and `app.include_router(push_router)`

**Step 5: Commit**

```bash
git add backend/app/api/push.py backend/app/workers/reminders.py backend/app/main.py
git commit -m "feat: add web push subscription and daily overdue payment reminder worker"
```

---

## Phase 10: Frontend — Auth & Layout

### Task 13: Supabase Auth Pages + Layout

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx` (login)
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/components/auth-guard.tsx`
- Create: `frontend/src/lib/supabase/middleware.ts`
- Create: `frontend/src/middleware.ts`

**Step 1: Create auth guard component**

`frontend/src/components/auth-guard.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session) {
          router.push("/");
        } else {
          setUser(session.user);
        }
        setLoading(false);
      }
    );
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) return null;

  return <>{children}</>;
}
```

**Step 2: Create login page with Supabase Auth UI**

Install: `cd frontend && npm install @supabase/auth-ui-react @supabase/auth-ui-shared`

`frontend/src/app/page.tsx`:
```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";

export default function LoginPage() {
  const supabase = createClient();
  const router = useRouter();

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (session) {
          // Sync user to backend
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/callback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: session.user.id,
              email: session.user.email,
              display_name: session.user.user_metadata.full_name || session.user.email,
              avatar_url: session.user.user_metadata.avatar_url || null,
            }),
          });
          router.push("/dashboard");
        }
      }
    );
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-6 text-center text-2xl font-bold">Splitify</h1>
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={[]}
          redirectTo={`${typeof window !== "undefined" ? window.location.origin : ""}/dashboard`}
        />
      </div>
    </div>
  );
}
```

**Step 3: Create dashboard page stub**

`frontend/src/app/dashboard/page.tsx`:
```tsx
"use client";

import { AuthGuard } from "@/components/auth-guard";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <div className="p-6">
        <h1 className="text-2xl font-bold">My Groups</h1>
        <p className="mt-2 text-gray-600">Your groups will appear here.</p>
      </div>
    </AuthGuard>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Supabase auth login page, auth guard, and dashboard stub"
```

---

## Phase 11: Frontend — Core Pages

### Task 14: Group List + Create Group Pages

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/groups/new/page.tsx`
- Create: `frontend/src/app/groups/[id]/page.tsx`
- Create: `frontend/src/app/join/[code]/page.tsx`
- Create: `frontend/src/types/index.ts`

Build out group list on dashboard, create group form, group detail page with member list + balances, and join-by-code page. Use `apiFetch` from `lib/api.ts` for all backend calls. Each page wrapped in `AuthGuard`.

**Step 1:** Create shared TypeScript types in `frontend/src/types/index.ts` matching backend schemas.

**Step 2:** Dashboard page: fetch groups via `GET /api/groups`, display as cards with group name and creation date. Link to `/groups/[id]`.

**Step 3:** Create group page: form with group name input, calls `POST /api/groups`, redirects to group detail.

**Step 4:** Group detail page: fetch group via `GET /api/groups/{id}`, show members, invite code, QR code (using `qrcode.react`), balances via `GET /api/groups/{id}/balances`.

**Step 5:** Join page: auto-joins via `POST /api/groups/join/{code}` on mount, redirects to group.

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add group list, create group, group detail, and join pages"
```

---

### Task 15: Receipt Upload + Detail Pages

**Files:**
- Create: `frontend/src/app/groups/[id]/receipts/page.tsx`
- Create: `frontend/src/app/groups/[id]/receipts/new/page.tsx`
- Create: `frontend/src/app/receipts/[id]/page.tsx`

**Step 1:** Receipt list page: fetch via `GET /api/groups/{id}/receipts`, show cards with merchant, total, status.

**Step 2:** Upload page: file input (camera on mobile), upload to Supabase Storage, then call `POST /api/groups/{id}/receipts` with the image URL. Show processing spinner.

**Step 3:** Receipt detail page: show extracted line items, merchant info, total. Subscribe to Supabase Realtime for status updates (processing → extracted).

**Step 4:** Assignment UI: for each line item, show checkboxes for group members. Assign/unassign calls `PUT /api/receipts/{id}/assignments`. Show share amounts.

**Step 5:** Payment section: "Who paid?" dropdown + amount field. Calls `POST /api/receipts/{id}/payments`.

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add receipt upload, detail, assignment, and payment UI"
```

---

### Task 16: Statistics Page

**Files:**
- Create: `frontend/src/app/groups/[id]/stats/page.tsx`

**Step 1:** Fetch stats via `GET /api/groups/{id}/stats?period=1mo`.

**Step 2:** Period selector: buttons for 1d, 1mo, 1yr.

**Step 3:** Display: total spending, receipt count, spending by user as a simple bar chart or table.

**Step 4: Commit**

```bash
git add frontend/src/app/groups/
git commit -m "feat: add group statistics page with period filtering"
```

---

## Phase 12: PWA Setup

### Task 17: PWA Configuration

**Files:**
- Create: `frontend/public/manifest.json`
- Modify: `frontend/src/app/layout.tsx` (meta tags)
- Modify: `frontend/next.config.ts` (next-pwa)
- Create: `frontend/public/sw.js` (or auto-generated)

**Step 1:** Create `manifest.json` with app name "Splitify", icons, theme color, `"display": "standalone"`.

**Step 2:** Add PWA meta tags to layout: `apple-touch-icon`, `apple-mobile-web-app-capable`, `theme-color`.

**Step 3:** Configure `next-pwa` in `next.config.ts` to generate service worker.

**Step 4:** Add web push registration in frontend: request notification permission, subscribe to push, send subscription to `POST /api/push/subscribe`.

**Step 5: Commit**

```bash
git add frontend/public/ frontend/src/app/layout.tsx frontend/next.config.ts
git commit -m "feat: configure PWA manifest, service worker, and web push registration"
```

---

## Phase 13: Frontend Design Polish

### Task 18: Apply Consistent Design System

Use the `frontend-design` skill to polish all pages with a cohesive design: consistent color palette, responsive layout, loading states, error states, empty states. Mobile-first since this is a PWA.

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1 | 1-3 | Project scaffolding, DB setup |
| 2 | 4 | All database models |
| 3 | 5 | Auth middleware |
| 4 | 6 | Groups CRUD + invites |
| 5 | 7-8 | Receipt upload + OCR |
| 6 | 9 | Line item assignments |
| 7 | 10 | Payments + balances |
| 8 | 11 | Statistics |
| 9 | 12 | Web push reminders |
| 10-11 | 13-16 | Frontend pages |
| 12 | 17 | PWA configuration |
| 13 | 18 | Design polish |

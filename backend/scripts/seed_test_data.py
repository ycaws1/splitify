"""Create test accounts and a test group.

Usage: python -m scripts.seed_test_data
Run from the backend/ directory.
"""

import asyncio
import uuid

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.user import User
from app.models.group import Group, GroupMember, GroupRole

SUPABASE_URL = settings.supabase_url
SERVICE_ROLE_KEY = settings.supabase_service_role_key

TEST_USERS = [
    {"email": "alice@test.com", "password": "testpass123", "display_name": "Alice"},
    {"email": "bob@test.com", "password": "testpass123", "display_name": "Bob"},
    {"email": "charlie@test.com", "password": "testpass123", "display_name": "Charlie"},
]

GROUP_NAME = "Test Group"


async def create_supabase_user(client: httpx.AsyncClient, email: str, password: str) -> str | None:
    """Create a user via Supabase Admin API. Returns user ID."""
    resp = await client.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers={
            "apikey": SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
        },
    )
    if resp.status_code == 200:
        user_id = resp.json()["id"]
        print(f"  Created Supabase user: {email} ({user_id})")
        return user_id
    elif resp.status_code == 422 and "already been registered" in resp.text:
        # User exists, fetch their ID
        list_resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
            },
        )
        for u in list_resp.json().get("users", []):
            if u["email"] == email:
                print(f"  User already exists: {email} ({u['id']})")
                return u["id"]
    else:
        print(f"  Error creating {email}: {resp.status_code} {resp.text}")
    return None


async def main():
    print("Creating test users in Supabase...")
    user_ids: list[tuple[str, str]] = []  # (user_id, display_name)

    async with httpx.AsyncClient() as client:
        for u in TEST_USERS:
            uid = await create_supabase_user(client, u["email"], u["password"])
            if uid:
                user_ids.append((uid, u["display_name"]))

    if not user_ids:
        print("No users created. Exiting.")
        return

    print(f"\nSyncing {len(user_ids)} users to local DB and creating group...")
    async with async_session_factory() as db:
        # Upsert users
        for uid_str, display_name in user_ids:
            uid = uuid.UUID(uid_str)
            result = await db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()
            if not user:
                email = next(u["email"] for u in TEST_USERS if u["display_name"] == display_name)
                user = User(id=uid, email=email, display_name=display_name)
                db.add(user)
                print(f"  Added user to DB: {display_name}")
            else:
                user.display_name = display_name
                print(f"  User already in DB: {display_name}")

        await db.flush()

        # Create group
        owner_id = uuid.UUID(user_ids[0][0])
        group = Group(
            name=GROUP_NAME,
            created_by=owner_id,
        )
        db.add(group)
        await db.flush()
        print(f"\n  Created group: {GROUP_NAME} (code: {group.invite_code})")

        # Add all users as members
        for i, (uid_str, display_name) in enumerate(user_ids):
            member = GroupMember(
                group_id=group.id,
                user_id=uuid.UUID(uid_str),
                role=GroupRole.owner if i == 0 else GroupRole.member,
            )
            db.add(member)
            print(f"  Added {display_name} to group as {'owner' if i == 0 else 'member'}")

        await db.commit()

    print("\nDone! Test accounts:")
    for u in TEST_USERS:
        print(f"  {u['email']} / {u['password']}")
    print(f"\nGroup: {GROUP_NAME}")


if __name__ == "__main__":
    asyncio.run(main())

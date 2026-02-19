import asyncio
import sys
from sqlalchemy import select, delete
from sqlalchemy.orm import aliased
from app.core.database import async_session_factory
from app.models.payment import Settlement
from app.models.group import Group
from app.models.user import User

TARGET_GROUP_NAME = "Trip to Danang"

async def fix_group_settlements():
    async with async_session_factory() as db:
        print("\n--- FINDING GROUP ---")
        groups = (await db.scalars(select(Group))).all()
        target_group = None
        for g in groups:
            if g.name == TARGET_GROUP_NAME:
                target_group = g
                break
        
        if not target_group:
            if groups:
                target_group = groups[0]
                print(f"Target group '{TARGET_GROUP_NAME}' not found, defaulting to first group: {target_group.name}")
            else:
                print("No groups found.")
                return

        group_id = target_group.id
        print(f"\n--- Fixing Group: {target_group.name} ({group_id}) ---\n")

        # 1. Preview Settlements to be deleted
        print("Finding settlements to delete...")
        u2 = aliased(User)
        settlements = (await db.execute(
            select(Settlement, User.display_name.label("from_name"), u2.display_name.label("to_name"))
            .join(User, User.id == Settlement.from_user)
            .join(u2, u2.id == Settlement.to_user)
            .where(Settlement.group_id == group_id)
        )).all()
        
        if not settlements:
            print("No settlements found to delete.")
            return

        print(f"Found {len(settlements)} settlements:")
        for s, from_n, to_n in settlements:
             print(f"- {from_n} -> {to_n}: {s.amount} ({'SETTLED' if s.is_settled else 'PENDING'})")

        # 2. Delete ALL settlements for this group
        print("\nDeleting all settlements...")
        await db.execute(delete(Settlement).where(Settlement.group_id == group_id))
        await db.commit()
        print("Deletion complete.")

if __name__ == "__main__":
    asyncio.run(fix_group_settlements())

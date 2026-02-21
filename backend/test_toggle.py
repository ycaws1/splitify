import asyncio
import os
import uuid
import sys

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:3tn45sp3IDBhDpk8@db.tthsmlircdieqddkjgxk.supabase.co:5432/postgres?ssl=require"

from app.core.database import async_session_factory
from sqlalchemy import select
from app.models.receipt import Receipt
from app.services.assignment_service import toggle_assignment

async def run():
    async with async_session_factory() as session:
        # Find any receipt
        result = await session.execute(select(Receipt).limit(1))
        receipt = result.scalar_one_or_none()
        if not receipt:
            print("No receipt found")
            return
            
        print(f"Testing on receipt: {receipt.id}")
        
        from app.models.receipt import LineItem
        from app.models.group import GroupMember
        
        # Find a line item
        result = await session.execute(select(LineItem).where(LineItem.receipt_id == receipt.id).limit(1))
        li = result.scalar_one_or_none()
        if not li:
            print("No line item found")
            return
            
        result = await session.execute(select(GroupMember).where(GroupMember.group_id == receipt.group_id).limit(1))
        member = result.scalar_one_or_none()
        if not member:
            print("No member found")
            return

        print(f"Testing on receipt: {receipt.id}, line_item: {li.id}, user: {member.user_id}")
        
        res = await toggle_assignment(
            session,
            receipt.id,
            li.id,
            member.user_id,
            None
        )
        print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(run())

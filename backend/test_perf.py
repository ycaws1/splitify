import asyncio
import time
import os
import uuid

# Set environment explicitly
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///example.db" # Default fallback, will see what config.py says
from app.core._db_setup import get_db, async_session_maker
from sqlalchemy import text
from app.services.calculation_service import get_group_financials
from app.services.group_service import list_user_groups

async def run():
    async with async_session_maker() as session:
        # 1. Grab first group ID
        res = await session.execute(text("SELECT id FROM groups LIMIT 1"))
        group_id = res.scalar()
        if not group_id:
            print("No groups found.")
            return
            
        print(f"Profiling queries for group_id: {group_id}")
        
        start = time.time()
        await get_group_financials(session, group_id)
        d1 = time.time() - start
        print(f"get_group_financials took {d1:.4f}s")
        
if __name__ == "__main__":
    asyncio.run(run())

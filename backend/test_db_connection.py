
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    print(f"Connecting to: {DATABASE_URL}")
    try:

        # Remove +asyncpg from scheme
        url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        # Try connecting with statement_cache_size=0
        conn = await asyncpg.connect(url, statement_cache_size=0)
        print("Successfully connected with statement_cache_size=0")
        
        version = await conn.fetchval("SELECT pg_catalog.version()")
        print(f"Version: {version}")
        
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())

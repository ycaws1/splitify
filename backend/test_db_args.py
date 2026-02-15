
import asyncio
import asyncpg
import uuid

async def test_connect_args():
    try:
        # This will fail to connect but we just want to see if it accepts the kwarg
        # We use a dummy DSN/host to avoid actual network but args are validated early usually?
        # Actually asyncpg validates kwargs in connect()
        await asyncpg.connect(
            user="user", password="password", database="db", host="127.0.0.1",
            statement_cache_size=0,
            prepared_statement_cache_size=0,
            prepared_statement_name_func=lambda: f"stmt_{uuid.uuid4()}"
        )
    except TypeError as e:
        print(f"TypeError caught: {e}")
    except Exception as e:
        print(f"Other error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_connect_args())
    except ImportError:
        print("asyncpg not installed")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _get_async_url(url: str) -> str:
    """Ensure the database URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url

_db_url = _get_async_url(settings.database_url)




print(f"DEBUG: database_url={_db_url}")

# Force pgbouncer settings to resolve "DuplicatePreparedStatementError"
# This confirms we are using transaction pooling which requires disabling prepared statements
_is_pgbouncer = True 
print(f"DEBUG: is_pgbouncer={_is_pgbouncer}")

engine = create_async_engine(
    _db_url,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
    },
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        yield session

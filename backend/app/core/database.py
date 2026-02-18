import uuid
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

class CachingDisabledConnection(asyncpg.Connection):
    def _get_unique_id(self, prefix: str) -> str:
        return f"__asyncpg_{uuid.uuid4()}__"
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _get_async_url(url: str) -> str:
    """Ensure the database URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

_db_url = _get_async_url(settings.database_url)

# Use a connection pool instead of NullPool to reuse TCP+TLS connections.
# With remote Supabase, connection setup is ~500-1000ms — pooling avoids this per-request.
# pgBouncer compatibility is handled by statement_cache_size=0 + CachingDisabledConnection.
engine = create_async_engine(
    _db_url,
    echo=False,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "connection_class": CachingDisabledConnection,
    },
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        yield session

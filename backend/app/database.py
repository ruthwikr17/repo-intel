from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

connect_args = {
    "timeout": 15,           # asyncpg connect timeout (seconds)
    "command_timeout": 30,   # asyncpg per-query timeout
}

# If DATABASE_URL uses the Supabase pooler on port 6543 (transaction mode),
# disable the statement cache as required by pgbouncer.
if ":6543" in settings.database_url:
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,      # test a connection before using it (handles stale ones)
    pool_recycle=240,        # recycle connections every 4 min (before the server drops them)
    pool_size=3,             # was 10; free instance has 512MB RAM
    max_overflow=5,          # was 20
    pool_timeout=20,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        from app.models import (
            User, Repository, RepositoryAnalysis,
            Opportunity, UserContribution, ApiLog, PdfReport
        )
        await conn.run_sync(Base.metadata.create_all)


async def create_tables():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        from app.models import (
            User, Repository, RepositoryAnalysis,
            Opportunity, UserContribution, ApiLog, PdfReport
        )
        await conn.run_sync(Base.metadata.create_all)

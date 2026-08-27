from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
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

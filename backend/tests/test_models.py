import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import (
    User, Repository, RepositoryAnalysis,
    Opportunity, UserContribution, ApiLog, PdfReport
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user = User(username="testuser", skill_level="intermediate")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.id is not None
    assert user.username == "testuser"
    assert user.repos_analyzed == 0


@pytest.mark.asyncio
async def test_create_repository(db_session: AsyncSession):
    repo = Repository(
        owner="django",
        name="django-rest-framework",
        full_name="django/django-rest-framework",
        url="https://github.com/django/django-rest-framework",
        stars=25000,
        language="Python",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    assert repo.id is not None
    assert repo.analysis_status == "pending"
    assert repo.stars == 25000


@pytest.mark.asyncio
async def test_create_api_log(db_session: AsyncSession):
    log = ApiLog(
        model="gemini-3.6-flash",
        project="project-a",
        calls_used=4,
        tokens_input=1000,
        tokens_output=2000,
        status="success"
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    assert log.id is not None
    assert log.model == "gemini-3.6-flash"
    assert log.calls_used == 4


@pytest.mark.asyncio
async def test_create_analysis(db_session: AsyncSession):
    repo = Repository(
        owner="psf",
        name="requests",
        full_name="psf/requests",
        url="https://github.com/psf/requests",
    )
    db_session.add(repo)
    await db_session.commit()

    analysis = RepositoryAnalysis(
        repo_id=repo.id,
        quality_tier="HIGH",
        summary="A simple HTTP library."
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)
    assert analysis.id is not None
    assert analysis.is_current is True

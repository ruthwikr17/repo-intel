import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.api_log import ApiLog
from app.services.quota_monitor import (
    log_api_call,
    get_daily_usage,
    get_remaining_capacity,
    select_tier,
    GEMINI_PROJECT_A_LIMIT,
    GEMINI_PROJECT_B_LIMIT,
    GROQ_LIMIT,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ApiLog.__table__.create)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(ApiLog.__table__.drop)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_initial_usage_is_zero(db_session):
    usage = await get_daily_usage(db_session)
    assert usage["gemini_project_a"] == 0
    assert usage["gemini_project_b"] == 0
    assert usage["groq"] == 0


@pytest.mark.asyncio
async def test_log_call_increments_usage(db_session):
    await log_api_call(db_session, "gemini-3.6-flash", "project-a", calls_used=4)
    usage = await get_daily_usage(db_session)
    assert usage["gemini_project_a"] == 4


@pytest.mark.asyncio
async def test_multiple_logs_accumulate(db_session):
    await log_api_call(db_session, "gemini-3.6-flash", "project-a", calls_used=4)
    await log_api_call(db_session, "gemini-3.6-flash", "project-a", calls_used=4)
    usage = await get_daily_usage(db_session)
    assert usage["gemini_project_a"] == 8


@pytest.mark.asyncio
async def test_groq_usage_tracked_separately(db_session):
    await log_api_call(db_session, "groq-llama-3.3", "groq-project-a", calls_used=4)
    usage = await get_daily_usage(db_session)
    assert usage["groq"] == 4
    assert usage["gemini_project_a"] == 0


@pytest.mark.asyncio
async def test_tier1_selected_when_quota_available(db_session):
    result = await select_tier(db_session)
    assert result["tier"] == "TIER_1"
    assert result["gemini_key"] is not None
    assert result["gemini_project"] == "project-a"


@pytest.mark.asyncio
async def test_tier1_falls_back_to_project_b(db_session):
    # Exhaust Project A
    await log_api_call(
        db_session, "gemini-3.6-flash", "project-a", calls_used=GEMINI_PROJECT_A_LIMIT
    )
    result = await select_tier(db_session)
    assert result["tier"] == "TIER_1"
    assert result["gemini_project"] == "project-b"


@pytest.mark.asyncio
async def test_tier2_selected_when_gemini_exhausted(db_session):
    # Exhaust both Gemini projects
    await log_api_call(
        db_session, "gemini-3.6-flash", "project-a", calls_used=GEMINI_PROJECT_A_LIMIT
    )
    await log_api_call(
        db_session, "gemini-3.6-flash", "project-b", calls_used=GEMINI_PROJECT_B_LIMIT
    )
    result = await select_tier(db_session)
    assert result["tier"] == "TIER_2"
    assert result["gemini_key"] is None


@pytest.mark.asyncio
async def test_queued_when_all_exhausted(db_session):
    # Exhaust everything
    await log_api_call(
        db_session, "gemini-3.6-flash", "project-a", calls_used=GEMINI_PROJECT_A_LIMIT
    )
    await log_api_call(
        db_session, "gemini-3.6-flash", "project-b", calls_used=GEMINI_PROJECT_B_LIMIT
    )
    await log_api_call(
        db_session, "groq-llama-3.3", "groq-project-a", calls_used=GROQ_LIMIT
    )
    result = await select_tier(db_session)
    assert result["tier"] == "QUEUED"


@pytest.mark.asyncio
async def test_remaining_capacity_calculation(db_session):
    capacity = await get_remaining_capacity(db_session)
    assert capacity["tier1_analyses_remaining"] == 50  # 200 Gemini / 4 calls
    assert capacity["total_analyses_remaining"] > 0

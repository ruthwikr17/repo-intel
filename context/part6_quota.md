# CONTEXT FILE: Part 6 - Quota Monitor & Tier Selection
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-5

- Part 1: FastAPI, Docker, PostgreSQL, Redis
- Part 2: GitHub API service
- Part 3: Repo cloning, AST analysis
- Part 4: Full database models (ApiLog table exists)
- Part 5: LLM service (run_llm_analysis, Tier 1 + Tier 2)

---

## What Part 6 Builds

- QuotaMonitor: tracks daily API usage in PostgreSQL (api_logs table)
- TierSelector: decides which tier to use for each analysis
- Logs every LLM call to database
- Exposes GET /api/admin/quota endpoint

---

## Files to Create or Modify

- backend/app/services/quota_monitor.py    (NEW)
- backend/app/routes/admin.py              (NEW)
- backend/app/main.py                      (MODIFY - add admin router)
- backend/tests/test_quota_monitor.py      (NEW)

---

## Quota Monitor Service

### backend/app/services/quota_monitor.py

```python
import asyncio
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.api_log import ApiLog
from app.config import get_settings

settings = get_settings()

# Daily limits
GEMINI_PROJECT_A_LIMIT = 100  # RPD per project
GEMINI_PROJECT_B_LIMIT = 100  # RPD per project
GROQ_LIMIT = 1000             # RPD total
GEMINI_CALLS_PER_TIER1 = 4   # Gemini calls per analysis in Tier 1
GROQ_CALLS_PER_TIER1 = 4     # Groq calls per analysis in Tier 1
GROQ_CALLS_PER_TIER2 = 8     # Groq calls per analysis in Tier 2


async def log_api_call(
    db: AsyncSession,
    model: str,
    project: str,
    calls_used: int,
    tokens_input: int = 0,
    tokens_output: int = 0,
    status: str = "success",
    analysis_id: int = None,
) -> None:
    """Log a single API call to the api_logs table."""
    log = ApiLog(
        model=model,
        project=project,
        calls_used=calls_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        status=status,
        analysis_id=analysis_id,
        date=date.today(),
        timestamp=datetime.now(),
    )
    db.add(log)
    await db.commit()


async def get_daily_usage(db: AsyncSession, target_date: date = None) -> dict:
    """
    Get total API calls used today per model/project.
    Returns dict with usage counts for each model.
    """
    if target_date is None:
        target_date = date.today()

    # Query api_logs for today
    result = await db.execute(
        select(
            ApiLog.model,
            ApiLog.project,
            func.sum(ApiLog.calls_used).label("total_calls"),
        )
        .where(ApiLog.date == target_date)
        .group_by(ApiLog.model, ApiLog.project)
    )
    rows = result.fetchall()

    usage = {
        "gemini_project_a": 0,
        "gemini_project_b": 0,
        "groq": 0,
    }

    for row in rows:
        model = row.model
        project = row.project
        total = row.total_calls or 0

        if model == "gemini-3.6-flash" and project == "project-a":
            usage["gemini_project_a"] += total
        elif model == "gemini-3.6-flash" and project == "project-b":
            usage["gemini_project_b"] += total
        elif model == "groq-llama-3.3":
            usage["groq"] += total

    usage["total_gemini"] = usage["gemini_project_a"] + usage["gemini_project_b"]
    return usage


async def get_remaining_capacity(db: AsyncSession) -> dict:
    """
    Calculate how many more analyses can be done today.
    Returns remaining capacity per tier and selected gemini project.
    """
    usage = await get_daily_usage(db)

    gemini_a_remaining = GEMINI_PROJECT_A_LIMIT - usage["gemini_project_a"]
    gemini_b_remaining = GEMINI_PROJECT_B_LIMIT - usage["gemini_project_b"]
    groq_remaining = GROQ_LIMIT - usage["groq"]

    # Total Gemini remaining across both projects
    total_gemini_remaining = gemini_a_remaining + gemini_b_remaining

    # Tier 1 analyses remaining (limited by Gemini)
    tier1_remaining = total_gemini_remaining // GEMINI_CALLS_PER_TIER1

    # Groq used by Tier 1 so far
    tier1_analyses_done = usage["total_gemini"] // GEMINI_CALLS_PER_TIER1
    groq_used_by_tier1 = tier1_analyses_done * GROQ_CALLS_PER_TIER1
    groq_for_tier2 = groq_remaining - max(
        0, (GROQ_CALLS_PER_TIER1 * tier1_remaining)
    )
    tier2_remaining = max(0, groq_for_tier2 // GROQ_CALLS_PER_TIER2)

    return {
        "usage": usage,
        "limits": {
            "gemini_project_a": GEMINI_PROJECT_A_LIMIT,
            "gemini_project_b": GEMINI_PROJECT_B_LIMIT,
            "groq": GROQ_LIMIT,
        },
        "remaining": {
            "gemini_project_a": max(0, gemini_a_remaining),
            "gemini_project_b": max(0, gemini_b_remaining),
            "groq": max(0, groq_remaining),
        },
        "tier1_analyses_remaining": max(0, tier1_remaining),
        "tier2_analyses_remaining": max(0, tier2_remaining),
        "total_analyses_remaining": max(0, tier1_remaining + tier2_remaining),
    }


async def select_tier(db: AsyncSession) -> dict:
    """
    Decide which tier to use for the next analysis.
    Returns:
      - tier: "TIER_1" or "TIER_2" or "QUEUED"
      - gemini_key: API key to use (None if Tier 2)
      - gemini_project: "project-a" or "project-b" (None if Tier 2)
    """
    usage = await get_daily_usage(db)

    gemini_a_remaining = GEMINI_PROJECT_A_LIMIT - usage["gemini_project_a"]
    gemini_b_remaining = GEMINI_PROJECT_B_LIMIT - usage["gemini_project_b"]
    groq_remaining = GROQ_LIMIT - usage["groq"]

    # Try Tier 1 with Project A first
    if gemini_a_remaining >= GEMINI_CALLS_PER_TIER1 and groq_remaining >= GROQ_CALLS_PER_TIER1:
        return {
            "tier": "TIER_1",
            "gemini_key": settings.gemini_api_key_project_a,
            "gemini_project": "project-a",
        }

    # Try Tier 1 with Project B
    if gemini_b_remaining >= GEMINI_CALLS_PER_TIER1 and groq_remaining >= GROQ_CALLS_PER_TIER1:
        return {
            "tier": "TIER_1",
            "gemini_key": settings.gemini_api_key_project_b,
            "gemini_project": "project-b",
        }

    # Gemini exhausted, try Tier 2 (Groq only)
    if groq_remaining >= GROQ_CALLS_PER_TIER2:
        return {
            "tier": "TIER_2",
            "gemini_key": None,
            "gemini_project": None,
        }

    # All quotas exhausted
    return {
        "tier": "QUEUED",
        "gemini_key": None,
        "gemini_project": None,
    }


async def log_analysis_calls(
    db: AsyncSession,
    tier: str,
    gemini_project: str = None,
    analysis_id: int = None,
) -> None:
    """
    Log all API calls made for one complete analysis.
    Called after a successful analysis to record usage.
    """
    if tier == "TIER_1":
        # Log Gemini calls
        await log_api_call(
            db=db,
            model="gemini-3.6-flash",
            project=gemini_project,
            calls_used=GEMINI_CALLS_PER_TIER1,
            status="success",
            analysis_id=analysis_id,
        )
        # Log Groq calls
        await log_api_call(
            db=db,
            model="groq-llama-3.3",
            project="groq-project-a",
            calls_used=GROQ_CALLS_PER_TIER1,
            status="success",
            analysis_id=analysis_id,
        )
    elif tier == "TIER_2":
        # Log all Groq calls
        await log_api_call(
            db=db,
            model="groq-llama-3.3",
            project="groq-project-a",
            calls_used=GROQ_CALLS_PER_TIER2,
            status="success",
            analysis_id=analysis_id,
        )
```

---

## Admin Route

### backend/app/routes/admin.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.quota_monitor import get_remaining_capacity

router = APIRouter()


@router.get("/admin/quota")
async def get_quota_status(db: AsyncSession = Depends(get_db)):
    """
    Returns current API quota usage and remaining capacity.
    Shows how many more analyses can be done today.
    """
    capacity = await get_remaining_capacity(db)
    return {
        "status": "ok",
        "date": str(__import__("datetime").date.today()),
        "quota": capacity,
    }
```

---

## Modify main.py

Add admin router. Add these lines:

```python
from app.routes.admin import router as admin_router
app.include_router(admin_router, prefix="/api", tags=["admin"])
```

---

## Tests

### backend/tests/test_quota_monitor.py

```python
import pytest
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
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
async def db():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_initial_usage_is_zero(db):
    usage = await get_daily_usage(db)
    assert usage["gemini_project_a"] == 0
    assert usage["gemini_project_b"] == 0
    assert usage["groq"] == 0


@pytest.mark.asyncio
async def test_log_call_increments_usage(db):
    await log_api_call(db, "gemini-3.6-flash", "project-a", calls_used=4)
    usage = await get_daily_usage(db)
    assert usage["gemini_project_a"] == 4


@pytest.mark.asyncio
async def test_multiple_logs_accumulate(db):
    await log_api_call(db, "gemini-3.6-flash", "project-a", calls_used=4)
    await log_api_call(db, "gemini-3.6-flash", "project-a", calls_used=4)
    usage = await get_daily_usage(db)
    assert usage["gemini_project_a"] == 8


@pytest.mark.asyncio
async def test_groq_usage_tracked_separately(db):
    await log_api_call(db, "groq-llama-3.3", "groq-project-a", calls_used=4)
    usage = await get_daily_usage(db)
    assert usage["groq"] == 4
    assert usage["gemini_project_a"] == 0


@pytest.mark.asyncio
async def test_tier1_selected_when_quota_available(db):
    result = await select_tier(db)
    assert result["tier"] == "TIER_1"
    assert result["gemini_key"] is not None
    assert result["gemini_project"] == "project-a"


@pytest.mark.asyncio
async def test_tier1_falls_back_to_project_b(db):
    # Exhaust Project A
    await log_api_call(
        db, "gemini-3.6-flash", "project-a",
        calls_used=GEMINI_PROJECT_A_LIMIT
    )
    result = await select_tier(db)
    assert result["tier"] == "TIER_1"
    assert result["gemini_project"] == "project-b"


@pytest.mark.asyncio
async def test_tier2_selected_when_gemini_exhausted(db):
    # Exhaust both Gemini projects
    await log_api_call(
        db, "gemini-3.6-flash", "project-a",
        calls_used=GEMINI_PROJECT_A_LIMIT
    )
    await log_api_call(
        db, "gemini-3.6-flash", "project-b",
        calls_used=GEMINI_PROJECT_B_LIMIT
    )
    result = await select_tier(db)
    assert result["tier"] == "TIER_2"
    assert result["gemini_key"] is None


@pytest.mark.asyncio
async def test_queued_when_all_exhausted(db):
    # Exhaust everything
    await log_api_call(
        db, "gemini-3.6-flash", "project-a",
        calls_used=GEMINI_PROJECT_A_LIMIT
    )
    await log_api_call(
        db, "gemini-3.6-flash", "project-b",
        calls_used=GEMINI_PROJECT_B_LIMIT
    )
    await log_api_call(
        db, "groq-llama-3.3", "groq-project-a",
        calls_used=GROQ_LIMIT
    )
    result = await select_tier(db)
    assert result["tier"] == "QUEUED"


@pytest.mark.asyncio
async def test_remaining_capacity_calculation(db):
    capacity = await get_remaining_capacity(db)
    assert capacity["tier1_analyses_remaining"] == 50  # 200 Gemini / 4 calls
    assert capacity["total_analyses_remaining"] > 0
```

---

## Validation Checklist

[ ] backend/app/services/quota_monitor.py created with all functions
[ ] backend/app/routes/admin.py created
[ ] backend/app/main.py includes admin_router
[ ] All 9 tests pass: pytest backend/tests/test_quota_monitor.py
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d
[ ] This endpoint returns valid quota data:

curl http://localhost:8000/api/admin/quota

Expected response shape:
{
  "status": "ok",
  "date": "2026-08-12",
  "quota": {
    "usage": {"gemini_project_a": 0, "gemini_project_b": 0, "groq": 0},
    "limits": {"gemini_project_a": 100, "gemini_project_b": 100, "groq": 1000},
    "remaining": {"gemini_project_a": 100, "gemini_project_b": 100, "groq": 1000},
    "tier1_analyses_remaining": 50,
    "tier2_analyses_remaining": 100,
    "total_analyses_remaining": 150
  }
}

[ ] tier1_analyses_remaining shows 50 (fresh start, no usage yet)
[ ] total_analyses_remaining shows 150

---

## What Part 7 Will Cover

- Opportunity scoring algorithm (pure math, no LLM)
- Scoring all GitHub issues and code quality issues
- Ranking by difficulty tier (beginner/intermediate/advanced)

Do NOT add scoring in Part 6.
Do NOT add Celery in Part 6.

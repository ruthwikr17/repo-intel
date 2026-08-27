from datetime import date, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.api_log import ApiLog

settings = get_settings()

# Daily limits
GEMINI_PROJECT_A_LIMIT = 100  # RPD per project
GEMINI_PROJECT_B_LIMIT = 100  # RPD per project
GROQ_LIMIT = 1000  # RPD total
GEMINI_CALLS_PER_TIER1 = 4  # Gemini calls per analysis in Tier 1
GROQ_CALLS_PER_TIER1 = 4  # Groq calls per analysis in Tier 1
GROQ_CALLS_PER_TIER2 = 8  # Groq calls per analysis in Tier 2


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
    groq_for_tier2 = groq_remaining - max(0, (GROQ_CALLS_PER_TIER1 * tier1_remaining))
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
    if (
        gemini_a_remaining >= GEMINI_CALLS_PER_TIER1
        and groq_remaining >= GROQ_CALLS_PER_TIER1
    ):
        return {
            "tier": "TIER_1",
            "gemini_key": settings.gemini_api_key_project_a,
            "gemini_project": "project-a",
        }

    # Try Tier 1 with Project B
    if (
        gemini_b_remaining >= GEMINI_CALLS_PER_TIER1
        and groq_remaining >= GROQ_CALLS_PER_TIER1
    ):
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

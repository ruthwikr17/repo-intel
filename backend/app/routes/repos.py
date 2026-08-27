from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from celery.result import AsyncResult

from app.database import get_db
from app.utils.validators import is_valid_github_url
from app.services.github_service import fetch_full_repo_data
from app.services.repo_analyzer import analyze_repository_locally
from app.services.matching_engine import get_top_matches
from app.schemas.user_profile import UserProfile
from app.schemas.analysis import (
    AnalysisRequest,
    TaskStatusResponse,
    OpportunityResponse,
    AnalysisResponse,
    RepoResponse,
)
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.tasks.analysis_task import run_full_analysis
from app.worker import celery_app

router = APIRouter()


# ─── Existing endpoints (keep as-is) ─────────────────────────────────────────


class RepoURLRequest:
    def __init__(self, url: str):
        self.url = url


from pydantic import BaseModel


class URLBody(BaseModel):
    url: str


@router.post("/repos/fetch-raw")
async def fetch_raw_repo_data(request: URLBody):
    if not is_valid_github_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    try:
        data = await fetch_full_repo_data(request.url)
        return {"status": "success", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")


@router.post("/repos/analyze-local")
async def analyze_repo_locally(request: URLBody):
    if not is_valid_github_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    result = analyze_repository_locally(request.url)
    return result


# ─── New endpoints ────────────────────────────────────────────────────────────


@router.post("/repos/analyze")
async def trigger_analysis(request: AnalysisRequest):
    """
    Trigger full async analysis pipeline via Celery.
    Returns task_id immediately. Poll /analyze/status/{task_id} for result.
    """
    if not is_valid_github_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    user_profile = {
        "skill_level": request.skill_level,
        "available_hours_per_week": request.available_hours_per_week,
        "preferred_categories": request.preferred_categories,
    }

    task = run_full_analysis.delay(request.url, user_profile)

    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Analysis started. Poll /api/repos/analyze/status/{task_id} for updates.",
    }


@router.get("/repos/analyze/status/{task_id}", response_model=TaskStatusResponse)
async def get_analysis_status(task_id: str):
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        state = task_result.state

        if state == "PENDING":
            return TaskStatusResponse(task_id=task_id, status="pending")

        elif state in ("STARTED", "PROGRESS"):
            try:
                meta = task_result.info or {}
                step = meta.get("step") if isinstance(meta, dict) else str(meta)
            except Exception:
                step = "Processing..."
            return TaskStatusResponse(task_id=task_id, status="processing", step=step)

        elif state == "SUCCESS":
            return TaskStatusResponse(
                task_id=task_id, status="completed", result=task_result.result
            )

        elif state == "FAILURE":
            try:
                error = str(task_result.info)
            except Exception:
                error = "Task failed. Check worker logs."
            return TaskStatusResponse(task_id=task_id, status="failed", error=error)

        return TaskStatusResponse(task_id=task_id, status=state.lower())

    except Exception as e:
        # Never crash the status endpoint
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=f"Could not retrieve task status: {str(e)}",
        )


@router.get("/repos/{repo_id}", response_model=RepoResponse)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get repository metadata by ID."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/repos/{repo_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get the current analysis for a repository."""
    result = await db.execute(
        select(RepositoryAnalysis).where(
            RepositoryAnalysis.repo_id == repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=404, detail="No analysis found for this repository"
        )
    return analysis


@router.get("/repos/{repo_id}/opportunities")
async def get_opportunities(
    repo_id: int,
    difficulty_tier: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all scored opportunities for a repository.
    Optional filter: difficulty_tier=beginner|intermediate|advanced
    """
    # Get current analysis id first
    analysis_result = await db.execute(
        select(RepositoryAnalysis.id).where(
            RepositoryAnalysis.repo_id == repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    current_analysis = analysis_result.scalar_one_or_none()

    if not current_analysis:
        return {"repo_id": repo_id, "total": 0, "opportunities": []}

    # Get opportunities for current analysis only
    query = select(Opportunity).where(
        Opportunity.repo_id == repo_id,
        Opportunity.analysis_id == current_analysis,  # Filter by current analysis
    )

    if difficulty_tier:
        query = query.where(Opportunity.difficulty_tier == difficulty_tier)

    query = query.order_by(Opportunity.overall_score.desc())

    result = await db.execute(query)
    opportunities = result.scalars().all()

    return {
        "repo_id": repo_id,
        "total": len(opportunities),
        "opportunities": [
            {
                "id": o.id,
                "title": o.title,
                "description": o.description,
                "category": o.category,
                "difficulty": o.difficulty,
                "impact": o.impact,
                "learning_value": o.learning_value,
                "overall_score": o.overall_score,
                "estimated_hours": o.estimated_hours,
                "difficulty_tier": o.difficulty_tier,
                "github_issue_number": o.github_issue_number,
                "github_issue_url": o.github_issue_url,
            }
            for o in opportunities
        ],
    }


@router.post("/repos/{repo_id}/opportunities/match")
async def get_matched_opportunities(
    repo_id: int,
    user_profile: UserProfile,
    db: AsyncSession = Depends(get_db),
):
    """
    Get opportunities ranked by suitability for a specific user profile.
    Body: UserProfile JSON
    """
    # Get current analysis id
    analysis_result = await db.execute(
        select(RepositoryAnalysis.id).where(
            RepositoryAnalysis.repo_id == repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    current_analysis = analysis_result.scalar_one_or_none()

    if not current_analysis:
        raise HTTPException(status_code=404, detail="No analysis found")

    # Get opportunities for current analysis only
    result = await db.execute(
        select(Opportunity)
        .where(
            Opportunity.repo_id == repo_id,
            Opportunity.analysis_id == current_analysis,
        )
        .order_by(Opportunity.overall_score.desc())
    )
    opportunities = result.scalars().all()

    if not opportunities:
        raise HTTPException(status_code=404, detail="No opportunities found")

    opp_dicts = [
        {
            "id": o.id,
            "title": o.title,
            "description": o.description,
            "category": o.category,
            "difficulty": o.difficulty,
            "impact": o.impact,
            "learning_value": o.learning_value,
            "feasibility": o.feasibility,
            "overall_score": o.overall_score,
            "estimated_hours": o.estimated_hours,
            "difficulty_tier": o.difficulty_tier,
            "github_issue_number": o.github_issue_number,
            "github_issue_url": o.github_issue_url,
        }
        for o in opportunities
    ]

    matched = get_top_matches(user_profile, opp_dicts)
    return {
        "repo_id": repo_id,
        "user_skill_level": user_profile.skill_level,
        **matched,
    }


@router.get("/repos")
async def list_analyzed_repos(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """List recently analyzed repositories."""
    result = await db.execute(
        select(Repository)
        .where(Repository.analysis_status == "completed")
        .order_by(Repository.last_analyzed_at.desc())
        .limit(limit)
    )
    repos = result.scalars().all()
    return {
        "total": len(repos),
        "repositories": [
            {
                "id": r.id,
                "full_name": r.full_name,
                "description": r.description,
                "language": r.language,
                "stars": r.stars,
                "last_analyzed_at": str(r.last_analyzed_at),
            }
            for r in repos
        ],
    }


@router.get("/repos/{repo_id}/opportunities/{opportunity_id}/ai-context")
async def get_ai_context(
    repo_id: int,
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a context prompt for AI chat redirect.
    Returns the full context string that gets passed to ChatGPT/Gemini/Claude.
    """
    # Get repo
    repo_result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get current analysis
    analysis_result = await db.execute(
        select(RepositoryAnalysis).where(
            RepositoryAnalysis.repo_id == repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    analysis = analysis_result.scalar_one_or_none()

    # Get opportunity
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Build tech stack string
    tech_stack = analysis.tech_stack or {} if analysis else {}
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "not detected"
    language = repo.language or "Unknown"

    # Build architecture snippet (truncated)
    arch_snippet = ""
    if analysis and analysis.architecture_explanation:
        arch_snippet = analysis.architecture_explanation[:400].replace("\n", " ")

    # Build context prompt
    context_prompt = f"""PROJECT CONTEXT
===============
Repository: {repo.full_name}
Description: {repo.description or 'No description'}
Language: {language}
Frameworks: {frameworks}
GitHub: {repo.url}

Architecture Overview:
{arch_snippet}

CONTRIBUTION TASK
=================
Title: {opp.title}
Category: {opp.category or 'general'}
Difficulty: {opp.difficulty}/10
Estimated Time: {opp.estimated_hours}h
Impact: {opp.impact}/10
Learning Value: {opp.learning_value}/10

What Needs to Be Done:
{opp.description or 'See GitHub issue for details'}
{f'GitHub Issue: {opp.github_issue_url}' if opp.github_issue_url else ''}

MY REQUEST
==========
I want to implement this contribution to {repo.full_name}.
Please help me with:
1. What exactly needs to be changed in the codebase
2. Which files to open first and why
3. Step-by-step implementation plan
4. What edge cases to handle
5. How to write tests for this change
6. How to write a good Pull Request description

Start by summarizing what you understand about the task,
then ask me any clarifying questions."""

    return {
        "context_prompt": context_prompt,
        "repo_full_name": repo.full_name,
        "opportunity_title": opp.title,
        "char_count": len(context_prompt),
    }


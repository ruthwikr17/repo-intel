# CONTEXT FILE: Part 10 - Full FastAPI Routes
# Project: RepoInsight
# Read the existing codebase before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-9

- Part 2: fetch_full_repo_data(url)
- Part 3: analyze_repository_locally(url)
- Part 5: run_llm_analysis(repo_data, gemini_key)
- Part 6: select_tier(db), log_analysis_calls(db)
- Part 7: score_all_opportunities(issues, ast_issues)
- Part 8: get_top_matches(user, opportunities), UserProfile schema
- Part 9: run_full_analysis Celery task, celery_app
- Part 4: Models: Repository, RepositoryAnalysis, Opportunity

Existing endpoints:
- GET  /api/health
- POST /api/repos/fetch-raw
- POST /api/repos/analyze-local
- GET  /api/admin/quota

---

## What Part 10 Builds

Complete API route layer connecting frontend to all backend services.
All new routes go in backend/app/routes/repos.py (extend existing file).

---

## Files to Modify or Create

- backend/app/routes/repos.py         (MODIFY - add all new endpoints)
- backend/app/schemas/analysis.py     (NEW - Pydantic response schemas)
- backend/tests/test_routes.py        (NEW - route tests)

---

## Response Schemas

### backend/app/schemas/analysis.py

```python
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class AnalysisRequest(BaseModel):
    url: str
    skill_level: Optional[str] = "intermediate"
    available_hours_per_week: Optional[int] = 5
    preferred_categories: Optional[list[str]] = []


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    step: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    difficulty: Optional[int]
    impact: Optional[int]
    learning_value: Optional[int]
    feasibility: Optional[int]
    overall_score: Optional[float]
    estimated_hours: Optional[int]
    difficulty_tier: Optional[str]
    github_issue_number: Optional[int]
    github_issue_url: Optional[str]
    suitability_score: Optional[float] = None
    match_percentage: Optional[int] = None
    recommended: Optional[bool] = None

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: int
    repo_id: int
    quality_tier: Optional[str]
    summary: Optional[str]
    architecture_explanation: Optional[str]
    code_walkthrough: Optional[str]
    common_patterns: Optional[str]
    gotchas_and_tips: Optional[str]
    setup_guide: Optional[str]
    tech_stack: Optional[dict]
    directory_structure: Optional[dict]
    open_issues: Optional[Any]
    contributors: Optional[Any]
    commits: Optional[Any]
    code_quality_metrics: Optional[dict]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class RepoResponse(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str
    url: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    open_issues_count: int
    analysis_status: str
    last_analyzed_at: Optional[datetime]

    class Config:
        from_attributes = True
```

---

## Updated repos.py

### backend/app/routes/repos.py

Replace entire file with this content:

```python
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
    """
    Poll Celery task status.
    States: PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    """
    task_result = AsyncResult(task_id, app=celery_app)
    state = task_result.state

    if state == "PENDING":
        return TaskStatusResponse(task_id=task_id, status="pending")

    elif state == "STARTED":
        meta = task_result.info or {}
        return TaskStatusResponse(
            task_id=task_id,
            status="started",
            step=meta.get("step")
        )

    elif state == "PROGRESS":
        meta = task_result.info or {}
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            step=meta.get("step")
        )

    elif state == "SUCCESS":
        return TaskStatusResponse(
            task_id=task_id,
            status="completed",
            result=task_result.result
        )

    elif state == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=str(task_result.info)
        )

    return TaskStatusResponse(task_id=task_id, status=state.lower())


@router.get("/repos/{repo_id}", response_model=RepoResponse)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get repository metadata by ID."""
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
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
        raise HTTPException(status_code=404, detail="No analysis found for this repository")
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
    query = select(Opportunity).where(Opportunity.repo_id == repo_id)

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
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.repo_id == repo_id)
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
```

---

## Tests

### backend/tests/test_routes.py

```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_health_still_works():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trigger_analysis_invalid_url():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/repos/analyze",
            json={"url": "https://gitlab.com/user/repo"}
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trigger_analysis_valid_url():
    mock_task = MagicMock()
    mock_task.id = "test-task-123"

    with patch("app.routes.repos.run_full_analysis") as mock_fn:
        mock_fn.delay.return_value = mock_task
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/repos/analyze",
                json={"url": "https://github.com/psf/requests"}
            )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == "test-task-123"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_get_analysis_status_pending():
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_result.info = None

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_get_analysis_status_completed():
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {"status": "completed", "analysis_id": 1}

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"]["analysis_id"] == 1


@pytest.mark.asyncio
async def test_get_repo_not_found():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/repos/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_repos_returns_list():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/repos")
    assert response.status_code == 200
    assert "repositories" in response.json()
```

---

## Validation Checklist

[ ] backend/app/schemas/__init__.py exists (empty ok)
[ ] backend/app/schemas/analysis.py created with all schemas
[ ] backend/app/routes/repos.py replaced with full content above
[ ] backend/tests/test_routes.py created
[ ] All 7 tests pass: pytest backend/tests/test_routes.py
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d

Manual endpoint tests:

1. Trigger analysis:
curl -X POST http://localhost:8000/api/repos/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/psf/requests", "skill_level": "intermediate"}'

Expected: {"task_id": "...", "status": "queued", "message": "..."}

2. Poll status (use task_id from above):
curl http://localhost:8000/api/repos/analyze/status/{task_id}

Expected after ~2 min: {"status": "completed", "result": {"analysis_id": 1, ...}}

3. Get repo:
curl http://localhost:8000/api/repos/1

4. Get opportunities:
curl http://localhost:8000/api/repos/1/opportunities

5. Get matched opportunities:
curl -X POST http://localhost:8000/api/repos/1/opportunities/match \
  -H "Content-Type: application/json" \
  -d '{"skill_level": "beginner", "available_hours_per_week": 3}'

6. List all analyzed repos:
curl http://localhost:8000/api/repos

[ ] All 6 curl commands return expected responses
[ ] Opportunities endpoint returns scored list with difficulty_tier
[ ] Match endpoint returns suitability_score and match_percentage

---

## What Part 11 Will Cover

React frontend:
- URL input form
- Analysis progress display
- Results dashboard
- Opportunities list with filters
- Match percentage display

Do NOT build frontend in Part 10.
Do NOT add PDF generation in Part 10.

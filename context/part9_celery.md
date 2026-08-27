# CONTEXT FILE: Part 9 - Celery Async Jobs
# Project: RepoInsight
# Read the existing codebase before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-8

- Part 2: github_service.py → fetch_full_repo_data(url)
- Part 3: repo_analyzer.py → analyze_repository_locally(url)
- Part 5: llm_service.py → run_llm_analysis(repo_data, gemini_key)
- Part 6: quota_monitor.py → select_tier(db), log_analysis_calls(db, ...)
- Part 7: scoring_engine.py → score_all_opportunities(issues, ast_issues)
- Part 8: matching_engine.py → get_top_matches(user, opportunities)
- Part 4: Models: Repository, RepositoryAnalysis, Opportunity, ApiLog

---

## What Part 9 Builds

Celery worker that runs the full analysis pipeline asynchronously.
One Celery task ties together all services from Parts 2-8.
Stores results in PostgreSQL.

---

## Files to Create or Modify

- backend/app/worker.py                  (NEW - Celery app instance)
- backend/app/tasks/analysis_task.py     (NEW - main async task)
- backend/app/tasks/__init__.py          (NEW - empty)
- backend/tests/test_analysis_task.py    (NEW - tests)

No new packages needed. Celery and Redis already in requirements.txt.

---

## Celery App

### backend/app/worker.py

```python
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "repoinsight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.analysis_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

---

## Analysis Task

### backend/app/tasks/analysis_task.py

```python
import asyncio
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import get_settings
from app.worker import celery_app
from app.services.github_service import fetch_full_repo_data, parse_repo_url
from app.services.repo_analyzer import analyze_repository_locally
from app.services.llm_service import run_llm_analysis
from app.services.quota_monitor import select_tier, log_analysis_calls
from app.services.scoring_engine import score_all_opportunities
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity

settings = get_settings()


def get_session_factory():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, name="app.tasks.analysis_task.run_full_analysis")
def run_full_analysis(self, repo_url: str, user_profile: dict = None):
    """
    Full analysis pipeline task.
    Steps:
      1. Fetch GitHub data
      2. Clone and analyze locally (AST, structure, tech stack)
      3. Select tier (quota monitor)
      4. Run LLM analysis (8 parallel calls)
      5. Score opportunities
      6. Save everything to database
      7. Return analysis_id

    Celery tasks are sync. asyncio.run() used to call async functions.
    """
    self.update_state(state="STARTED", meta={"step": "Fetching GitHub data"})

    try:
        # Step 1: GitHub API data
        github_data = asyncio.run(fetch_full_repo_data(repo_url))

        self.update_state(state="PROGRESS", meta={"step": "Analyzing repository"})

        # Step 2: Local analysis (clone + AST)
        local_analysis = analyze_repository_locally(repo_url)

        # Combine data for LLM
        combined_data = {
            **github_data,
            "tech_stack": local_analysis.get("tech_stack", {}),
            "directory_structure": local_analysis.get("directory_structure", {}),
            "ast_analysis": local_analysis.get("ast_analysis", {}),
        }

        self.update_state(state="PROGRESS", meta={"step": "Selecting AI tier"})

        # Step 3: Select tier
        session_factory = get_session_factory()

        async def get_tier():
            async with session_factory() as db:
                return await select_tier(db)

        tier_info = asyncio.run(get_tier())

        if tier_info["tier"] == "QUEUED":
            return {
                "status": "queued",
                "message": "Daily quota exhausted. Try again tomorrow.",
            }

        self.update_state(state="PROGRESS", meta={"step": "Running AI analysis"})

        # Step 4: LLM analysis
        llm_results = asyncio.run(
            run_llm_analysis(
                combined_data,
                gemini_key=tier_info.get("gemini_key"),
            )
        )

        self.update_state(state="PROGRESS", meta={"step": "Scoring opportunities"})

        # Step 5: Score opportunities
        github_issues = github_data.get("issues", [])
        ast_issues = local_analysis.get("ast_analysis", {}).get("all_issues", [])
        scored = score_all_opportunities(github_issues, ast_issues)

        self.update_state(state="PROGRESS", meta={"step": "Saving to database"})

        # Step 6: Save to database
        async def save_results():
            async with session_factory() as db:
                owner = github_data.get("owner")
                repo_name = github_data.get("repo")
                metadata = github_data.get("metadata", {})

                # Upsert repository
                existing = await db.execute(
                    select(Repository).where(
                        Repository.full_name == metadata.get("full_name")
                    )
                )
                repo = existing.scalar_one_or_none()

                if not repo:
                    repo = Repository(
                        owner=owner,
                        name=repo_name,
                        full_name=metadata.get("full_name", f"{owner}/{repo_name}"),
                        url=f"https://github.com/{owner}/{repo_name}",
                        description=metadata.get("description"),
                        language=metadata.get("language"),
                        stars=metadata.get("stars", 0),
                        forks=metadata.get("forks", 0),
                        open_issues_count=metadata.get("open_issues_count", 0),
                        topics=metadata.get("topics", []),
                        license=metadata.get("license"),
                    )
                    db.add(repo)
                    await db.flush()

                repo.analysis_status = "completed"
                repo.last_analyzed_at = datetime.now()
                repo.cached_github_data = github_data
                repo.cached_until = datetime.now() + timedelta(hours=24)

                # Mark old analyses as not current
                old = await db.execute(
                    select(RepositoryAnalysis).where(
                        RepositoryAnalysis.repo_id == repo.id,
                        RepositoryAnalysis.is_current == True,
                    )
                )
                for old_analysis in old.scalars().all():
                    old_analysis.is_current = False

                # Save new analysis
                analysis = RepositoryAnalysis(
                    repo_id=repo.id,
                    quality_tier=llm_results.get("quality_tier"),
                    apis_used=llm_results.get("apis_used"),
                    summary=llm_results.get("summary"),
                    architecture_explanation=llm_results.get("architecture_explanation"),
                    code_walkthrough=llm_results.get("code_walkthrough"),
                    common_patterns=llm_results.get("common_patterns"),
                    gotchas_and_tips=llm_results.get("common_patterns"),
                    setup_guide=llm_results.get("setup_guide"),
                    tech_stack=combined_data.get("tech_stack"),
                    directory_structure=combined_data.get("directory_structure"),
                    open_issues=github_data.get("issues"),
                    contributors=github_data.get("contributors"),
                    commits=github_data.get("commits"),
                    code_quality_metrics=combined_data.get("ast_analysis"),
                    is_current=True,
                )
                db.add(analysis)
                await db.flush()

                # Save opportunities
                for opp in scored.get("all", []):
                    opportunity = Opportunity(
                        analysis_id=analysis.id,
                        repo_id=repo.id,
                        title=opp.get("title", "")[:255],
                        description=opp.get("description", "")[:300],
                        category=opp.get("category"),
                        github_issue_number=opp.get("github_issue_number"),
                        github_issue_url=opp.get("github_issue_url"),
                        difficulty=opp.get("difficulty"),
                        learning_value=opp.get("learning_value"),
                        impact=opp.get("impact"),
                        feasibility=opp.get("feasibility"),
                        overall_score=opp.get("overall_score"),
                        estimated_hours=opp.get("estimated_hours"),
                        difficulty_tier=opp.get("difficulty_tier"),
                    )
                    db.add(opportunity)

                # Log API usage
                await log_analysis_calls(
                    db=db,
                    tier=tier_info["tier"],
                    gemini_project=tier_info.get("gemini_project"),
                    analysis_id=analysis.id,
                )

                await db.commit()
                return analysis.id

        analysis_id = asyncio.run(save_results())

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "quality_tier": llm_results.get("quality_tier"),
            "opportunities_found": scored.get("total_count", 0),
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise
```

---

## docker-compose.yml Update

Add Celery worker service. Add this to the services section:

```yaml
  worker:
    build: ./backend
    command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
    environment:
      DATABASE_URL: postgresql+asyncpg://repoinsight:repoinsight@db:5432/repoinsight
      REDIS_URL: redis://cache:6379/0
    env_file:
      - ./backend/.env
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    volumes:
      - ./backend:/app
    restart: unless-stopped
```

---

## Tests

### backend/tests/test_analysis_task.py

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


MOCK_GITHUB_DATA = {
    "owner": "psf",
    "repo": "requests",
    "metadata": {
        "full_name": "psf/requests",
        "description": "HTTP library",
        "stars": 54000,
        "forks": 10000,
        "open_issues_count": 200,
        "language": "Python",
        "license": "Apache",
        "topics": ["http", "python"],
    },
    "issues": [
        {"number": 1, "title": "Fix bug", "body": "bug",
         "labels": ["bug"], "comments": 3,
         "html_url": "https://github.com/psf/requests/issues/1"}
    ],
    "contributors": [],
    "languages": {"Python": 390000},
    "commits": [],
}

MOCK_LOCAL_ANALYSIS = {
    "status": "success",
    "tech_stack": {"frameworks": ["pytest"], "has_tests": True,
                   "has_docker": False, "has_ci": True, "manifests_found": []},
    "directory_structure": {"name": "requests", "type": "dir", "children": []},
    "ast_analysis": {"files_analyzed": 5, "avg_complexity": 4.0,
                     "total_functions": 20, "total_classes": 3,
                     "all_issues": [], "all_imports": [], "file_results": {}},
}

MOCK_LLM_RESULTS = {
    "quality_tier": "MEDIUM",
    "apis_used": ["groq-llama-3.3"],
    "summary": "A simple HTTP library.",
    "architecture_explanation": "Well structured.",
    "code_walkthrough": "Start with sessions.py.",
    "common_patterns": "Uses adapters pattern.",
    "setup_guide": "pip install requests",
    "contributor_guide_narrative": "Great project to contribute to.",
    "executive_summary": "Adopt this library.",
    "code_quality_report": "Good quality overall.",
}

MOCK_TIER = {
    "tier": "TIER_2",
    "gemini_key": None,
    "gemini_project": None,
}


def test_task_registered():
    from app.worker import celery_app
    assert "app.tasks.analysis_task.run_full_analysis" in celery_app.tasks


@patch("app.tasks.analysis_task.asyncio.run")
@patch("app.tasks.analysis_task.analyze_repository_locally")
@patch("app.tasks.analysis_task.get_session_factory")
def test_task_returns_queued_when_quota_exhausted(
    mock_factory, mock_local, mock_asyncio_run
):
    mock_local.return_value = MOCK_LOCAL_ANALYSIS

    # First asyncio.run = github data, second = tier selection
    mock_asyncio_run.side_effect = [
        MOCK_GITHUB_DATA,
        {"tier": "QUEUED", "gemini_key": None, "gemini_project": None},
    ]

    from app.tasks.analysis_task import run_full_analysis
    task = run_full_analysis
    task.request = MagicMock()
    task.update_state = MagicMock()

    result = task.run("https://github.com/psf/requests")
    assert result["status"] == "queued"


def test_celery_app_has_correct_broker():
    from app.worker import celery_app
    from app.config import get_settings
    settings = get_settings()
    assert celery_app.conf.broker_url == settings.redis_url
```

---

## Validation Checklist

[ ] backend/app/worker.py created
[ ] backend/app/tasks/__init__.py created (empty)
[ ] backend/app/tasks/analysis_task.py created
[ ] docker-compose.yml has worker service added
[ ] All 3 tests pass: pytest backend/tests/test_analysis_task.py
[ ] Docker rebuilt with worker: docker-compose down && docker-compose up --build -d
[ ] Worker container starts without errors:
    docker-compose logs worker
    Should show: "celery@... ready" with no import errors

[ ] Task registered check:
    docker-compose exec worker celery -A app.worker.celery_app inspect registered
    Should list: app.tasks.analysis_task.run_full_analysis

---

## What Part 10 Will Cover

Full FastAPI routes that tie everything together:
- POST /api/repos/analyze (trigger Celery task)
- GET /api/repos/analyze/status/{task_id}
- GET /api/repos/{repo_id}
- GET /api/repos/{repo_id}/opportunities
- GET /api/repos/{repo_id}/opportunities/{opp_id}/match

Do NOT add these routes in Part 9.

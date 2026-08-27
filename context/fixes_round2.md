# CONTEXT FILE: Fix Round 2 - asyncio.run() in Celery Worker
# Project: RepoInsight
# Root Cause: asyncio.run() cannot be called from a running event loop
# Celery workers already have an event loop; asyncio.run() creates another one.
# Fix: Replace all asyncio.run() calls with a proper async runner.

---

## The Problem

In backend/app/tasks/analysis_task.py, every async function is called like:
    result = asyncio.run(some_async_function())

This crashes because Celery workers run inside an event loop already.
The fix is to run async code using a new dedicated event loop explicitly.

---

## Fix: Replace analysis_task.py Entirely

### backend/app/tasks/analysis_task.py

Replace the entire file with this content:

```python
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import get_settings
from app.worker import celery_app
from app.services.github_service import fetch_full_repo_data
from app.services.repo_analyzer import analyze_repository_locally
from app.services.llm_service import run_llm_analysis, generate_ai_opportunities
from app.services.quota_monitor import select_tier, log_analysis_calls
from app.services.scoring_engine import score_all_opportunities
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity

settings = get_settings()


def run_async(coro):
    """
    Safely run an async coroutine from a sync Celery task.
    Creates a brand new event loop each time to avoid
    'asyncio.run() cannot be called from a running event loop' error.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def get_session_factory():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, name="app.tasks.analysis_task.run_full_analysis")
def run_full_analysis(self, repo_url: str, user_profile: dict = None):
    """
    Full analysis pipeline task.
    Uses run_async() instead of asyncio.run() to avoid event loop conflicts.
    """

    try:
        # Step 1: GitHub API data
        self.update_state(state="PROGRESS", meta={"step": "Fetching GitHub data"})
        github_data = run_async(fetch_full_repo_data(repo_url))

        # Step 2: Local analysis (clone + AST)
        self.update_state(state="PROGRESS", meta={"step": "Analyzing repository"})
        local_analysis = analyze_repository_locally(repo_url)

        # Combine data for LLM
        combined_data = {
            **github_data,
            "tech_stack": local_analysis.get("tech_stack", {}),
            "directory_structure": local_analysis.get("directory_structure", {}),
            "ast_analysis": local_analysis.get("ast_analysis", {}),
        }

        # Step 3: Select tier
        self.update_state(state="PROGRESS", meta={"step": "Selecting AI tier"})
        session_factory = get_session_factory()

        async def get_tier():
            async with session_factory() as db:
                return await select_tier(db)

        tier_info = run_async(get_tier())

        if tier_info["tier"] == "QUEUED":
            return {
                "status": "queued",
                "message": "Daily quota exhausted. Try again tomorrow.",
            }

        # Step 4: LLM analysis (8 parallel calls)
        self.update_state(state="PROGRESS", meta={"step": "Running AI analysis"})
        llm_results = run_async(
            run_llm_analysis(
                combined_data,
                gemini_key=tier_info.get("gemini_key"),
            )
        )

        # Step 4.5: AI contribution suggestions (9th call)
        self.update_state(state="PROGRESS", meta={"step": "Generating contribution ideas"})
        ai_suggestions = run_async(
            generate_ai_opportunities(
                combined_data,
                gemini_key=tier_info.get("gemini_key"),
            )
        )

        # Step 5: Score opportunities
        self.update_state(state="PROGRESS", meta={"step": "Scoring opportunities"})
        github_issues = github_data.get("issues", [])
        ast_issues = local_analysis.get("ast_analysis", {}).get("all_issues", [])
        scored = score_all_opportunities(github_issues, ast_issues, ai_suggestions)

        # Step 6: Save to database
        self.update_state(state="PROGRESS", meta={"step": "Saving to database"})

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
                old_result = await db.execute(
                    select(RepositoryAnalysis).where(
                        RepositoryAnalysis.repo_id == repo.id,
                        RepositoryAnalysis.is_current == True,
                    )
                )
                for old_analysis in old_result.scalars().all():
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

        analysis_id = run_async(save_results())

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "quality_tier": llm_results.get("quality_tier"),
            "opportunities_found": scored.get("total_count", 0),
        }

    except Exception as e:
        # Log the real error clearly
        import traceback
        print(f"[TASK ERROR] {str(e)}")
        print(traceback.format_exc())
        # Re-raise as a simple string to avoid Celery serialization issues
        raise Exception(f"Analysis failed: {str(e)}")
```

---

## Also Fix: Celery Worker Config

### backend/app/worker.py

Add these two lines to celery_app.conf.update to fix the exception serialization error:

```python
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Add these two lines:
    task_always_eager=False,
    result_backend_transport_options={"retry_on_timeout": True},
)
```

---

## Also Fix: Frontend - Handle QUEUED and FAILURE States

### backend/app/routes/repos.py

The status endpoint currently crashes if Celery can't decode a failed task.
Update get_analysis_status to handle this:

```python
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
                task_id=task_id,
                status="completed",
                result=task_result.result
            )

        elif state == "FAILURE":
            try:
                error = str(task_result.info)
            except Exception:
                error = "Task failed. Check worker logs."
            return TaskStatusResponse(
                task_id=task_id,
                status="failed",
                error=error
            )

        return TaskStatusResponse(task_id=task_id, status=state.lower())

    except Exception as e:
        # Never crash the status endpoint
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=f"Could not retrieve task status: {str(e)}"
        )
```

---

## Also Fix: Frontend - Show Error Instead of Silently Going Home

### frontend/src/hooks/useAnalysis.ts

Update the poll function to handle failed status:

```typescript
const poll = async () => {
  try {
    const status = await getTaskStatus(taskId);
    setTaskStatus(status);

    if (status.status === 'completed' || status.status === 'failed' || status.status === 'queued') {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setLoading(false);
      // If failed, set error message
      if (status.status === 'failed') {
        setError(status.error || 'Analysis failed. Please try again.');
      }
    }
  } catch (e) {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setError('Failed to get analysis status. Check if backend is running.');
    setLoading(false);
  }
};
```

### frontend/src/App.tsx

Add handling for failed status so it shows error on home page instead of going blank:

```typescript
// Replace the existing completion check with:
useEffect(() => {
  if (taskStatus?.status === 'completed' && taskStatus.result?.analysis_id) {
    setRepoId(taskStatus.result.analysis_id);
    setView('results');
  }
  // Failed: stay on home page, error will show via useAnalysis hook
}, [taskStatus]);
```

---

## Validation Checklist

[ ] analysis_task.py fully replaced (no asyncio.run() anywhere)
[ ] run_async() helper function is present at top of file
[ ] worker.py has new conf options
[ ] Status endpoint wrapped in try/except
[ ] Frontend shows error message on failure instead of going home silently
[ ] Rebuild: docker-compose down && docker-compose up --build -d
[ ] Test: submit a repo URL
[ ] Worker logs show NO RuntimeError
[ ] Worker logs show step-by-step progress messages
[ ] Analysis completes and results load in frontend

If worker still crashes after rebuild, run:
    docker-compose logs worker --tail=50
and share the NEW error (it will be different now - the real underlying error).

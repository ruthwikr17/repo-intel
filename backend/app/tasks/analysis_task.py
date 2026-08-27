import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import get_settings
from app.worker import celery_app
from app.services.github_mcp_service import fetch_full_repo_data_mcp as fetch_full_repo_data
from app.services.github_mcp_service import parse_repo_url
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
    Run async coroutine safely from sync Celery task.
    Creates fresh event loop each time.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            # Cancel pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        finally:
            loop.close()
            asyncio.set_event_loop(None)


def make_engine():
    """
    Create a fresh SQLAlchemy async engine.
    Must be called inside each event loop - never shared across loops.
    NullPool prevents connection reuse across loops.
    """
    from sqlalchemy.pool import NullPool

    return create_async_engine(
        settings.database_url,
        poolclass=NullPool,  # Critical: no connection pooling across loops
    )


@celery_app.task(bind=True, name="app.tasks.analysis_task.run_full_analysis")
def run_full_analysis(self, repo_url: str, user_profile: dict = None):
    """
    Full analysis pipeline.
    Each run_async() call gets its own engine to avoid loop conflicts.
    """
    import traceback

    try:
        # Step 1: GitHub API data
        self.update_state(state="PROGRESS", meta={"step": "Fetching GitHub data"})
        github_data = run_async(fetch_full_repo_data(repo_url))

        # Step 2: Local analysis (sync - no event loop needed)
        self.update_state(state="PROGRESS", meta={"step": "Analyzing repository"})
        local_analysis = analyze_repository_locally(repo_url)

        combined_data = {
            **github_data,
            "tech_stack": local_analysis.get("tech_stack", {}),
            "directory_structure": local_analysis.get("directory_structure", {}),
            "ast_analysis": local_analysis.get("ast_analysis", {}),
        }

        # Step 3: Select tier (fresh engine inside)
        self.update_state(state="PROGRESS", meta={"step": "Selecting AI tier"})

        async def get_tier():
            engine = make_engine()
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                result = await select_tier(db)
            await engine.dispose()
            return result

        tier_info = run_async(get_tier())

        if tier_info["tier"] == "QUEUED":
            return {
                "status": "queued",
                "message": "Daily quota exhausted. Try again tomorrow.",
            }

        # Step 4: LLM analysis
        self.update_state(state="PROGRESS", meta={"step": "Running AI analysis"})
        llm_results = run_async(
            run_llm_analysis(
                combined_data,
                gemini_key=tier_info.get("gemini_key"),
            )
        )

        # Step 4.5: AI contribution suggestions
        self.update_state(
            state="PROGRESS", meta={"step": "Generating contribution ideas"}
        )
        ai_suggestions = run_async(
            generate_ai_opportunities(
                combined_data,
                gemini_key=tier_info.get("gemini_key"),
            )
        )

        # Step 5: Score opportunities (sync - pure math)
        self.update_state(state="PROGRESS", meta={"step": "Scoring opportunities"})
        github_issues = github_data.get("issues", [])
        ast_issues = local_analysis.get("ast_analysis", {}).get("all_issues", [])
        scored = score_all_opportunities(github_issues, ast_issues, ai_suggestions)

        # Step 6: Save to database (fresh engine inside)
        self.update_state(state="PROGRESS", meta={"step": "Saving to database"})

        async def save_results():
            engine = make_engine()
            factory = async_sessionmaker(engine, expire_on_commit=False)

            try:
                async with factory() as db:
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
                        architecture_explanation=llm_results.get(
                            "architecture_explanation"
                        ),
                        code_walkthrough=llm_results.get("code_walkthrough"),
                        common_patterns=llm_results.get("common_patterns"),
                        gotchas_and_tips=llm_results.get("gotchas_and_tips"),
                        setup_guide=llm_results.get("setup_guide"),
                        tech_stack=combined_data.get("tech_stack"),
                        directory_structure=combined_data.get("directory_structure"),
                        open_issues=github_data.get("issues"),
                        contributors=github_data.get("contributors"),
                        commits=github_data.get("commits"),
                        code_quality_metrics=combined_data.get("ast_analysis"),
                        ai_suggestions=ai_suggestions,
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
                            description=(opp.get("what_to_do") or opp.get("description", ""))[:500],
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
                    return {"analysis_id": analysis.id, "repo_id": repo.id}
            finally:
                await engine.dispose()

        ids = run_async(save_results())

        return {
            "status": "completed",
            "analysis_id": ids["analysis_id"],
            "repo_id": ids["repo_id"],
            "quality_tier": llm_results.get("quality_tier"),
            "opportunities_found": scored.get("total_count", 0),
        }

    except Exception as e:
        print(f"[TASK ERROR] {str(e)}")
        print(traceback.format_exc())
        raise Exception(f"Analysis failed: {str(e)}")

# CONTEXT FILE: Fix Round 4 - Frontend Loading Failure + Duplicates
# Project: RepoInsight
# Backend is working correctly. These are frontend + data issues only.

---

## Issue 1: "Failed to load analysis results"

ROOT CAUSE:
The Celery task returns:
  { "status": "completed", "analysis_id": 7, "repo_id": ... }

But the task actually returns analysis_id (the RepositoryAnalysis table id),
NOT the repository id. The frontend then calls:
  getAnalysis(analysis_id)  ← passes 7 (analysis id)
  getOpportunities(analysis_id) ← passes 7

But the API endpoints expect repo_id, not analysis_id:
  GET /api/repos/{repo_id}/analysis
  GET /api/repos/{repo_id}/opportunities

So it's querying repo 7 which doesn't exist, causing 404 = "Failed to load".

FIX: The task must return repo_id, not analysis_id.

### Fix backend/app/tasks/analysis_task.py

In the save_results() function, change the return value:
```python
await db.commit()
# Return BOTH ids
return {"analysis_id": analysis.id, "repo_id": repo.id}
```

Change the last return statement of run_full_analysis to:
```python
ids = run_async(save_results())

return {
    "status": "completed",
    "analysis_id": ids["analysis_id"],
    "repo_id": ids["repo_id"],
    "quality_tier": llm_results.get("quality_tier"),
    "opportunities_found": scored.get("total_count", 0),
}
```

### Fix frontend/src/App.tsx

Update the completion handler to use repo_id:
```typescript
useEffect(() => {
  if (
    taskStatus?.status === 'completed' &&
    taskStatus.result?.repo_id
  ) {
    setRepoId(taskStatus.result.repo_id);  // Use repo_id not analysis_id
    setView('results');
  }
}, [taskStatus]);
```

### Fix frontend/src/types/index.ts

Update AnalysisResult type:
```typescript
export interface AnalysisResult {
  status: string;
  analysis_id: number;
  repo_id: number;       // Add this
  quality_tier: string;
  opportunities_found: number;
}
```

---

## Issue 2: Duplicate Opportunities

ROOT CAUSE:
Every opportunity appears twice because:
1. First analysis run (before fixes) saved opportunities with ids 1-24
2. Second analysis run (after fixes) saved NEW opportunities with ids 79-101
Both analyses point to the same repo_id=1.
The GET /api/repos/{repo_id}/opportunities returns ALL opportunities
for that repo across ALL analyses, causing duplicates.

FIX A: Filter opportunities by current analysis only (best fix).

### Fix backend/app/routes/repos.py

Update get_opportunities endpoint to join with current analysis:

```python
@router.get("/repos/{repo_id}/opportunities")
async def get_opportunities(
    repo_id: int,
    difficulty_tier: str = None,
    db: AsyncSession = Depends(get_db),
):
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
```

FIX B: Also update match endpoint the same way.

### Fix backend/app/routes/repos.py - match endpoint

```python
@router.post("/repos/{repo_id}/opportunities/match")
async def get_matched_opportunities(
    repo_id: int,
    user_profile: UserProfile,
    db: AsyncSession = Depends(get_db),
):
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
```

---

## Issue 3: Gemini model still wrong in some places

Search the ENTIRE codebase for any remaining references to:
- "gemini-3.6-flash"
- "gemini-3.6-flash"
- "gemini-3.6-flash"

Replace ALL occurrences with: "gemini-3.6-flash"

Most likely in backend/app/services/llm_service.py

---

## Validation Checklist

[ ] analysis_task.py save_results() returns {"analysis_id": x, "repo_id": y}
[ ] analysis_task.py final return includes both analysis_id and repo_id
[ ] App.tsx uses taskStatus.result.repo_id to set repoId
[ ] types/index.ts AnalysisResult includes repo_id field
[ ] repos.py get_opportunities filters by current analysis_id
[ ] repos.py match endpoint filters by current analysis_id
[ ] No "gemini-2.5" strings anywhere in codebase
[ ] Rebuild: docker-compose down && docker-compose up --build -d
[ ] Re-analyze psf/requests (new analysis)
[ ] Results page loads without "Failed to load" error
[ ] Opportunities shows ~24 items (not 48 duplicates)
[ ] Architecture tab shows real content (not Gemini error)

Do NOT delete old data from database. The filter fix handles it.

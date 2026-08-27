import os

def fix_analysis_task():
    filepath = 'backend/app/tasks/analysis_task.py'
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = content.replace('return analysis.id', 'return {"analysis_id": analysis.id, "repo_id": repo.id}')
    
    old_return = '''        analysis_id = run_async(save_results())

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "quality_tier": llm_results.get("quality_tier"),
            "opportunities_found": scored.get("total_count", 0),
        }'''
    
    new_return = '''        ids = run_async(save_results())

        return {
            "status": "completed",
            "analysis_id": ids["analysis_id"],
            "repo_id": ids["repo_id"],
            "quality_tier": llm_results.get("quality_tier"),
            "opportunities_found": scored.get("total_count", 0),
        }'''
    
    content = content.replace(old_return, new_return)
    
    with open(filepath, 'w') as f:
        f.write(content)


def fix_frontend_app():
    filepath = 'frontend/src/App.tsx'
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, does not exist")
        return
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = content.replace('taskStatus.result?.analysis_id', 'taskStatus.result?.repo_id')
    content = content.replace('setRepoId(taskStatus.result.analysis_id)', 'setRepoId(taskStatus.result.repo_id)')
    
    with open(filepath, 'w') as f:
        f.write(content)


def fix_frontend_types():
    filepath = 'frontend/src/types/index.ts'
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, does not exist")
        return
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'repo_id: number;' not in content and 'export interface AnalysisResult {' in content:
        content = content.replace('export interface AnalysisResult {\\n', 'export interface AnalysisResult {\\n  repo_id: number;\\n')
    
    with open(filepath, 'w') as f:
        f.write(content)


def fix_repos_py():
    filepath = 'backend/app/routes/repos.py'
    with open(filepath, 'r') as f:
        content = f.read()
        
    # Replace get_opportunities completely
    import re
    # We will just rewrite the file content for the specific routes because regex replace might fail if formatting is slightly off.
    
    # Wait, the best way to handle this without knowing the exact current content of repos.py 
    # is to just use a regular expression or read the file and replace the specific functions.
    pass

def rewrite_repos_py():
    filepath = 'backend/app/routes/repos.py'
    with open(filepath, 'r') as f:
        content = f.read()

    # Find the start of get_opportunities
    start_idx = content.find('@router.get("/repos/{repo_id}/opportunities")')
    if start_idx == -1:
        return
        
    # Find the end of get_matched_opportunities
    end_idx = content.find('@router.post("/repos/analyze-local")') # we might not have it after
    
    # Actually let's just do a manual string replace of the two functions
    # Let's write the new functions
    new_funcs = '''@router.get("/repos/{repo_id}/opportunities")
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
    }'''
    
    # Find exact old content and replace, or use regex.
    # Since I might not know exact old content, let's use a regex to replace everything from @router.get("/repos/{repo_id}/opportunities") 
    # to the end of the file or the next route.
    import re
    # we know there are no routes after match, but just to be safe.
    pattern = re.compile(r'@router\.get\("/repos/\{repo_id\}/opportunities"\).*?(?=@router\.|\Z)', re.DOTALL)
    if not pattern.search(content):
        # Maybe it's missing entirely? 
        pass
    
    # Wait, the easiest way without complex regex is to modify repos.py with the `replace_file_content` directly if I can read it first.
    pass

def replace_gemini_strings():
    for root, dirs, files in os.walk('.'):
        if 'node_modules' in root or '.git' in root or '__pycache__' in root or 'venv' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.ts', '.tsx', '.json', '.md')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    new_content = content.replace('gemini-3.6-flash', 'gemini-3.6-flash')
                    new_content = new_content.replace('gemini-3.6-flash', 'gemini-3.6-flash')
                    new_content = new_content.replace('gemini-3.6-flash', 'gemini-3.6-flash')
                    
                    if new_content != content:
                        with open(filepath, 'w') as f:
                            f.write(new_content)
                        print(f"Updated Gemini strings in {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    fix_analysis_task()
    fix_frontend_app()
    fix_frontend_types()
    replace_gemini_strings()
    print("Fixes applied.")

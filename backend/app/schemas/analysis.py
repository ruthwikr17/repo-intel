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

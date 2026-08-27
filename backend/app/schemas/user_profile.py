from pydantic import BaseModel, Field
from typing import Optional

class UserProfile(BaseModel):
    skill_level: str = Field(
        default="intermediate",
        description="beginner / intermediate / advanced"
    )
    primary_language: Optional[str] = Field(
        default=None,
        description="e.g. Python, JavaScript, Java"
    )
    interests: list[str] = Field(
        default=[],
        description="e.g. ['backend', 'frontend', 'devops']"
    )
    available_hours_per_week: int = Field(
        default=5,
        description="Hours available per week to contribute"
    )
    preferred_categories: list[str] = Field(
        default=[],
        description="e.g. ['bug', 'feature', 'documentation']"
    )
    learning_goal: Optional[str] = Field(
        default=None,
        description="e.g. 'learn testing', 'improve architecture skills'"
    )

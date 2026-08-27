# CONTEXT FILE: Part 8 - Matching Algorithm
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-7

- Part 7: Opportunity scoring engine (score_all_opportunities)
- Opportunities have: difficulty, impact, learning_value, feasibility,
  overall_score, difficulty_tier, estimated_hours, category

---

## What Part 8 Builds

Matching algorithm that re-ranks scored opportunities
for a specific user based on their profile.
No database. No LLM. Pure math only.

---

## Files to Create

- backend/app/services/matching_engine.py    (NEW)
- backend/app/schemas/user_profile.py        (NEW - Pydantic schema)
- backend/tests/test_matching_engine.py      (NEW)

---

## User Profile Schema

### backend/app/schemas/user_profile.py

```python
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
```

---

## Matching Engine

### backend/app/services/matching_engine.py

```python
from app.schemas.user_profile import UserProfile

# Skill level → numeric value
SKILL_LEVEL_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}

# Difficulty tier → numeric value
TIER_LEVEL_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}


def calculate_skill_match(user: UserProfile, opportunity: dict) -> float:
    """
    How well does user skill match opportunity difficulty?
    Perfect match = 1.0, one level off = 0.6, two levels off = 0.2
    """
    user_level = SKILL_LEVEL_MAP.get(user.skill_level, 2)
    opp_level = TIER_LEVEL_MAP.get(opportunity.get("difficulty_tier", "intermediate"), 2)
    diff = abs(user_level - opp_level)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.6
    else:
        return 0.2


def calculate_time_match(user: UserProfile, opportunity: dict) -> float:
    """
    Can the user complete this in their available time?
    Estimated hours vs available hours per week.
    """
    available = user.available_hours_per_week
    needed = opportunity.get("estimated_hours", 5)

    if needed <= available:
        return 1.0
    elif needed <= available * 1.5:
        return 0.7
    elif needed <= available * 2:
        return 0.4
    else:
        return 0.1


def calculate_interest_match(user: UserProfile, opportunity: dict) -> float:
    """
    Does this opportunity match user's preferred categories?
    """
    if not user.preferred_categories:
        return 0.7  # neutral if no preference

    category = opportunity.get("category", "")
    if category in user.preferred_categories:
        return 1.0
    return 0.4


def calculate_suitability(user: UserProfile, opportunity: dict) -> float:
    """
    Master matching formula:
    Suitability = (SkillMatch x TimeMatch x InterestMatch x LearningValue) / Difficulty

    Returns float 0.0 - 1.0
    """
    skill_match = calculate_skill_match(user, opportunity)
    time_match = calculate_time_match(user, opportunity)
    interest_match = calculate_interest_match(user, opportunity)
    learning_value = opportunity.get("learning_value", 5) / 10.0
    difficulty = opportunity.get("difficulty", 5) / 10.0

    if difficulty == 0:
        difficulty = 0.1

    raw = (skill_match * time_match * interest_match * learning_value) / difficulty
    # Normalize to 0-1 range (cap at 1.0)
    return round(min(1.0, raw), 3)


def match_opportunities(
    user: UserProfile,
    opportunities: list[dict],
) -> list[dict]:
    """
    Re-rank opportunities for a specific user.
    Adds suitability_score and match_percentage to each opportunity.
    Sorts by suitability_score descending.
    Returns annotated list.
    """
    matched = []
    for opp in opportunities:
        suitability = calculate_suitability(user, opp)
        annotated = {
            **opp,
            "suitability_score": suitability,
            "match_percentage": int(suitability * 100),
            "recommended": suitability >= 0.6,
        }
        matched.append(annotated)

    matched.sort(key=lambda x: x["suitability_score"], reverse=True)
    return matched


def get_top_matches(
    user: UserProfile,
    opportunities: list[dict],
    top_n: int = 5,
) -> dict:
    """
    Returns top N matches for user with summary breakdown.
    """
    all_matched = match_opportunities(user, opportunities)
    top = all_matched[:top_n]
    recommended = [o for o in all_matched if o["recommended"]]
    not_recommended = [o for o in all_matched if not o["recommended"]]

    return {
        "top_matches": top,
        "recommended": recommended,
        "not_recommended": not_recommended,
        "total_matched": len(all_matched),
        "recommended_count": len(recommended),
        "user_skill_level": user.skill_level,
    }
```

---

## Tests

### backend/tests/test_matching_engine.py

```python
import pytest
from app.schemas.user_profile import UserProfile
from app.services.matching_engine import (
    calculate_skill_match,
    calculate_time_match,
    calculate_interest_match,
    calculate_suitability,
    match_opportunities,
    get_top_matches,
)

BEGINNER_USER = UserProfile(
    skill_level="beginner",
    available_hours_per_week=3,
    preferred_categories=["documentation", "bug"],
)

INTERMEDIATE_USER = UserProfile(
    skill_level="intermediate",
    available_hours_per_week=8,
    preferred_categories=["feature", "refactor"],
)

BEGINNER_OPP = {
    "title": "Fix typo in README",
    "difficulty": 2,
    "difficulty_tier": "beginner",
    "estimated_hours": 1,
    "learning_value": 3,
    "category": "documentation",
    "overall_score": 59.0,
}

ADVANCED_OPP = {
    "title": "Refactor auth system",
    "difficulty": 9,
    "difficulty_tier": "advanced",
    "estimated_hours": 20,
    "learning_value": 9,
    "category": "refactor",
    "overall_score": 456.0,
}

MEDIUM_OPP = {
    "title": "Add CSV export",
    "difficulty": 5,
    "difficulty_tier": "intermediate",
    "estimated_hours": 6,
    "learning_value": 7,
    "category": "feature",
    "overall_score": 287.0,
}


def test_skill_match_perfect():
    assert calculate_skill_match(BEGINNER_USER, BEGINNER_OPP) == 1.0

def test_skill_match_two_levels_off():
    assert calculate_skill_match(BEGINNER_USER, ADVANCED_OPP) == 0.2

def test_skill_match_one_level_off():
    assert calculate_skill_match(BEGINNER_USER, MEDIUM_OPP) == 0.6

def test_time_match_fits():
    assert calculate_time_match(BEGINNER_USER, BEGINNER_OPP) == 1.0

def test_time_match_too_long():
    assert calculate_time_match(BEGINNER_USER, ADVANCED_OPP) == 0.1

def test_interest_match_hits():
    assert calculate_interest_match(BEGINNER_USER, BEGINNER_OPP) == 1.0

def test_interest_match_misses():
    assert calculate_interest_match(BEGINNER_USER, MEDIUM_OPP) == 0.4

def test_interest_match_no_preference():
    user = UserProfile(skill_level="intermediate")
    assert calculate_interest_match(user, MEDIUM_OPP) == 0.7

def test_suitability_beginner_gets_high_score_on_beginner_task():
    score = calculate_suitability(BEGINNER_USER, BEGINNER_OPP)
    assert score >= 0.5

def test_suitability_beginner_gets_low_score_on_advanced_task():
    score = calculate_suitability(BEGINNER_USER, ADVANCED_OPP)
    assert score < 0.3

def test_match_opportunities_adds_fields():
    result = match_opportunities(INTERMEDIATE_USER, [BEGINNER_OPP, MEDIUM_OPP])
    for opp in result:
        assert "suitability_score" in opp
        assert "match_percentage" in opp
        assert "recommended" in opp

def test_match_opportunities_sorted_descending():
    result = match_opportunities(INTERMEDIATE_USER, [BEGINNER_OPP, MEDIUM_OPP, ADVANCED_OPP])
    scores = [o["suitability_score"] for o in result]
    assert scores == sorted(scores, reverse=True)

def test_get_top_matches_returns_structure():
    result = get_top_matches(INTERMEDIATE_USER, [BEGINNER_OPP, MEDIUM_OPP, ADVANCED_OPP])
    assert "top_matches" in result
    assert "recommended" in result
    assert "not_recommended" in result
    assert result["total_matched"] == 3

def test_recommended_flag_true_above_threshold():
    result = match_opportunities(BEGINNER_USER, [BEGINNER_OPP])
    assert result[0]["recommended"] is True

def test_recommended_flag_false_for_poor_match():
    result = match_opportunities(BEGINNER_USER, [ADVANCED_OPP])
    assert result[0]["recommended"] is False
```

---

## Validation Checklist

[ ] backend/app/schemas/ folder created
[ ] backend/app/schemas/__init__.py created (empty)
[ ] backend/app/schemas/user_profile.py created
[ ] backend/app/services/matching_engine.py created
[ ] backend/tests/test_matching_engine.py created
[ ] All 15 tests pass: pytest backend/tests/test_matching_engine.py
[ ] No Docker rebuild needed (no new packages)

Manual check in Python shell:
    from app.schemas.user_profile import UserProfile
    from app.services.matching_engine import get_top_matches

    user = UserProfile(skill_level="beginner", available_hours_per_week=3,
                       preferred_categories=["documentation"])
    opps = [
        {"title": "Fix typo", "difficulty": 2, "difficulty_tier": "beginner",
         "estimated_hours": 1, "learning_value": 3, "category": "documentation",
         "overall_score": 59.0},
        {"title": "Refactor auth", "difficulty": 9, "difficulty_tier": "advanced",
         "estimated_hours": 20, "learning_value": 9, "category": "refactor",
         "overall_score": 456.0},
    ]
    result = get_top_matches(user, opps)
    print(result["top_matches"][0]["title"])  # Should be "Fix typo"
    print(result["recommended_count"])        # Should be 1

[ ] Beginner user gets "Fix typo" as top match
[ ] Advanced opportunity marked as not recommended for beginner

---

## Session Handoff Note (Save This)

PROJECT: RepoInsight
Full-Stack Repository Analysis System with AI-Powered
Matching Engine for Open Source Contributors

COMPLETED PARTS:
- Part 1: Project setup, Docker, FastAPI, PostgreSQL, Redis
- Part 2: GitHub API service
- Part 3: Repo cloning, AST analysis
- Part 4: Database models, Alembic
- Part 5: LLM service (Gemini + Groq, 8 parallel calls)
- Part 6: Quota monitor, tier selection
- Part 7: Opportunity scoring engine
- Part 8: Matching algorithm, UserProfile schema

WORKING ENDPOINTS:
- GET  /api/health
- POST /api/repos/fetch-raw
- POST /api/repos/analyze-local
- GET  /api/admin/quota

NEXT: Part 9 - Celery async jobs

PARTS REMAINING:
9.  Celery Async Jobs
10. All FastAPI Routes (full analysis pipeline)
11. React Frontend
12. PDF Generation
13. Docker & Deployment

WORKFLOW:
- Claude generates CONTEXT_PARTX.md files
- Give to Antigravity (Gemini Flash) to build
- It creates create_files.py, run it locally
- Verify, report back, continue

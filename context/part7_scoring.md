# CONTEXT FILE: Part 7 - Opportunity Scoring Engine
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-6

- Part 1: FastAPI, Docker, PostgreSQL, Redis
- Part 2: GitHub API service
- Part 3: Repo cloning, AST analysis
- Part 4: Full database models (Opportunity table exists)
- Part 5: LLM service (8 parallel calls)
- Part 6: Quota monitor, tier selection, /api/admin/quota

---

## What Part 7 Builds

Pure algorithmic scoring engine. No LLM involved.
Takes raw GitHub issues and AST-detected code issues,
scores each one, assigns difficulty tier, and returns
ranked list of contribution opportunities.

---

## Files to Create

- backend/app/services/scoring_engine.py     (NEW)
- backend/tests/test_scoring_engine.py       (NEW)

Do NOT modify any other files.

---

## Scoring Engine

### backend/app/services/scoring_engine.py

```python
from typing import Any

# ─── Scoring Constants ────────────────────────────────────────────────────────

# Difficulty tier thresholds (hours)
BEGINNER_MAX_HOURS = 3
INTERMEDIATE_MAX_HOURS = 8

# Issue label → difficulty hint mapping
LABEL_DIFFICULTY_MAP = {
    "good first issue": 2,
    "good-first-issue": 2,
    "beginner": 2,
    "easy": 2,
    "starter": 2,
    "help wanted": 5,
    "help-wanted": 5,
    "enhancement": 5,
    "bug": 5,
    "feature": 6,
    "feature request": 6,
    "performance": 7,
    "security": 8,
    "refactor": 6,
    "architecture": 9,
    "breaking change": 9,
}

# Issue label → impact hint mapping
LABEL_IMPACT_MAP = {
    "bug": 8,
    "security": 10,
    "performance": 8,
    "breaking change": 9,
    "enhancement": 6,
    "feature": 7,
    "feature request": 7,
    "documentation": 4,
    "docs": 4,
    "help wanted": 6,
    "good first issue": 3,
}

# Category → learning value mapping
CATEGORY_LEARNING_MAP = {
    "bug": 7,
    "feature": 8,
    "documentation": 4,
    "refactor": 7,
    "testing": 5,
    "performance": 9,
    "security": 9,
    "dependency": 3,
}

# Code smell → difficulty mapping
CODE_SMELL_DIFFICULTY_MAP = {
    "too many parameters": 4,
    "too long": 5,
    "high complexity": 7,
    "duplication": 6,
    "unused import": 2,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def clamp(value: float, min_val: float = 1.0, max_val: float = 10.0) -> int:
    return int(max(min_val, min(max_val, round(value))))


def get_difficulty_from_labels(labels: list[str]) -> int:
    """Infer difficulty from GitHub issue labels."""
    for label in labels:
        label_lower = label.lower()
        if label_lower in LABEL_DIFFICULTY_MAP:
            return LABEL_DIFFICULTY_MAP[label_lower]
    return 5  # default medium


def get_impact_from_labels(labels: list[str]) -> int:
    """Infer impact from GitHub issue labels."""
    for label in labels:
        label_lower = label.lower()
        if label_lower in LABEL_IMPACT_MAP:
            return LABEL_IMPACT_MAP[label_lower]
    return 5  # default medium


def detect_category_from_labels(labels: list[str], title: str) -> str:
    """Detect opportunity category from labels and title."""
    labels_lower = [l.lower() for l in labels]
    title_lower = title.lower()

    if any(l in labels_lower for l in ["bug", "fix"]):
        return "bug"
    if any(l in labels_lower for l in ["documentation", "docs"]):
        return "documentation"
    if any(l in labels_lower for l in ["security"]):
        return "security"
    if any(l in labels_lower for l in ["performance"]):
        return "performance"
    if any(l in labels_lower for l in ["feature", "enhancement", "feature request"]):
        return "feature"
    if "refactor" in title_lower:
        return "refactor"
    if "test" in title_lower:
        return "testing"
    if "doc" in title_lower or "readme" in title_lower:
        return "documentation"
    return "feature"


def estimate_hours(difficulty: int, category: str) -> int:
    """Estimate hours based on difficulty and category."""
    base_hours = {1: 1, 2: 1, 3: 2, 4: 3, 5: 5, 6: 6, 7: 10, 8: 16, 9: 20, 10: 30}
    hours = base_hours.get(difficulty, 5)
    # Documentation is faster
    if category == "documentation":
        hours = max(1, hours // 2)
    return hours


def assign_difficulty_tier(difficulty: int, estimated_hours: int) -> str:
    """Assign beginner/intermediate/advanced based on difficulty and hours."""
    if difficulty <= 3 and estimated_hours <= BEGINNER_MAX_HOURS:
        return "beginner"
    elif difficulty <= 6 and estimated_hours <= INTERMEDIATE_MAX_HOURS:
        return "intermediate"
    else:
        return "advanced"


def calculate_score(impact: int, learning: int, feasibility: int, difficulty: int) -> float:
    """
    Core scoring formula:
    Score = (Impact x Learning x Feasibility) - Difficulty
    Higher score = better opportunity.
    """
    return (impact * learning * feasibility) - difficulty


# ─── Score GitHub Issues ──────────────────────────────────────────────────────

def score_github_issue(issue: dict) -> dict:
    """
    Score a single GitHub issue as a contribution opportunity.
    Input: issue dict from GitHub API (number, title, body, labels, comments)
    Output: scored opportunity dict
    """
    labels = issue.get("labels", [])
    title = issue.get("title", "")
    comments = issue.get("comments", 0)

    # Determine scores
    difficulty = get_difficulty_from_labels(labels)
    impact = get_impact_from_labels(labels)
    category = detect_category_from_labels(labels, title)
    learning = CATEGORY_LEARNING_MAP.get(category, 5)

    # More comments = better documented = easier to understand
    if comments >= 5:
        feasibility = 8
    elif comments >= 2:
        feasibility = 6
    else:
        feasibility = 4

    # Good first issue label boosts feasibility
    labels_lower = [l.lower() for l in labels]
    if "good first issue" in labels_lower or "good-first-issue" in labels_lower:
        feasibility = min(10, feasibility + 2)
        difficulty = min(difficulty, 3)

    # Clamp all values
    difficulty = clamp(difficulty)
    impact = clamp(impact)
    learning = clamp(learning)
    feasibility = clamp(feasibility)

    hours = estimate_hours(difficulty, category)
    tier = assign_difficulty_tier(difficulty, hours)
    score = calculate_score(impact, learning, feasibility, difficulty)

    return {
        "title": title,
        "description": (issue.get("body") or "")[:300],
        "category": category,
        "source": "github_issue",
        "github_issue_number": issue.get("number"),
        "github_issue_url": issue.get("html_url", ""),
        "difficulty": difficulty,
        "impact": impact,
        "learning_value": learning,
        "feasibility": feasibility,
        "overall_score": round(score, 2),
        "estimated_hours": hours,
        "difficulty_tier": tier,
    }


# ─── Score Code Smells ────────────────────────────────────────────────────────

def score_code_smell(issue: dict) -> dict:
    """
    Score a single AST-detected code smell as a contribution opportunity.
    Input: issue dict from AST analysis {file, issue}
    Output: scored opportunity dict
    """
    issue_text = issue.get("issue", "").lower()
    file_path = issue.get("file", "")

    # Detect smell type
    smell_type = "refactor"
    difficulty = 5
    for keyword, diff in CODE_SMELL_DIFFICULTY_MAP.items():
        if keyword in issue_text:
            difficulty = diff
            if keyword == "unused import":
                smell_type = "cleanup"
            elif keyword in ("too many parameters", "too long"):
                smell_type = "refactor"
            elif keyword == "high complexity":
                smell_type = "refactor"
            break

    impact = 5       # code quality improvements are medium impact
    learning = 6     # refactoring teaches good patterns
    feasibility = 7  # code smells are usually straightforward to fix
    category = "refactor"

    difficulty = clamp(difficulty)
    impact = clamp(impact)
    learning = clamp(learning)
    feasibility = clamp(feasibility)

    hours = estimate_hours(difficulty, category)
    tier = assign_difficulty_tier(difficulty, hours)
    score = calculate_score(impact, learning, feasibility, difficulty)

    title = f"Fix: {issue.get('issue', 'Code quality issue')}"
    description = f"Code quality issue detected in {file_path}: {issue.get('issue', '')}"

    return {
        "title": title[:255],
        "description": description[:300],
        "category": category,
        "source": "ast_analysis",
        "github_issue_number": None,
        "github_issue_url": None,
        "difficulty": difficulty,
        "impact": impact,
        "learning_value": learning,
        "feasibility": feasibility,
        "overall_score": round(score, 2),
        "estimated_hours": hours,
        "difficulty_tier": tier,
    }


# ─── Master Scoring Function ──────────────────────────────────────────────────

def score_all_opportunities(
    github_issues: list[dict],
    ast_issues: list[dict],
    max_total: int = 30,
) -> dict:
    """
    Score all opportunities from both sources.
    Returns sorted lists by tier and overall ranking.

    Input:
      - github_issues: list of issues from GitHub API
      - ast_issues: list of issues from AST analysis
      - max_total: max opportunities to return

    Output:
      - all: full ranked list
      - beginner: beginner-tier only
      - intermediate: intermediate-tier only
      - advanced: advanced-tier only
      - total_count: int
    """
    scored = []

    # Score GitHub issues
    for issue in github_issues:
        try:
            scored.append(score_github_issue(issue))
        except Exception:
            continue

    # Score AST code smells (cap at 10 to avoid noise)
    for issue in ast_issues[:10]:
        try:
            scored.append(score_code_smell(issue))
        except Exception:
            continue

    # Sort by overall_score descending
    scored.sort(key=lambda x: x["overall_score"], reverse=True)

    # Cap total
    scored = scored[:max_total]

    # Split by tier
    beginner = [o for o in scored if o["difficulty_tier"] == "beginner"]
    intermediate = [o for o in scored if o["difficulty_tier"] == "intermediate"]
    advanced = [o for o in scored if o["difficulty_tier"] == "advanced"]

    return {
        "all": scored,
        "beginner": beginner,
        "intermediate": intermediate,
        "advanced": advanced,
        "total_count": len(scored),
        "beginner_count": len(beginner),
        "intermediate_count": len(intermediate),
        "advanced_count": len(advanced),
    }
```

---

## Tests

### backend/tests/test_scoring_engine.py

```python
import pytest
from app.services.scoring_engine import (
    score_github_issue,
    score_code_smell,
    score_all_opportunities,
    calculate_score,
    assign_difficulty_tier,
    get_difficulty_from_labels,
    get_impact_from_labels,
    clamp,
)

# ─── Unit Tests ───────────────────────────────────────────────────────────────

def test_clamp_within_range():
    assert clamp(5) == 5

def test_clamp_below_min():
    assert clamp(0) == 1

def test_clamp_above_max():
    assert clamp(15) == 10

def test_calculate_score():
    score = calculate_score(impact=9, learning=6, feasibility=7, difficulty=6)
    assert score == (9 * 6 * 7) - 6  # 372

def test_difficulty_tier_beginner():
    assert assign_difficulty_tier(2, 2) == "beginner"

def test_difficulty_tier_intermediate():
    assert assign_difficulty_tier(5, 6) == "intermediate"

def test_difficulty_tier_advanced():
    assert assign_difficulty_tier(8, 16) == "advanced"

def test_label_difficulty_good_first_issue():
    assert get_difficulty_from_labels(["good first issue"]) == 2

def test_label_difficulty_security():
    assert get_difficulty_from_labels(["security"]) == 8

def test_label_difficulty_default():
    assert get_difficulty_from_labels(["unknown-label"]) == 5

def test_label_impact_bug():
    assert get_impact_from_labels(["bug"]) == 8

def test_label_impact_security():
    assert get_impact_from_labels(["security"]) == 10


# ─── Integration Tests ────────────────────────────────────────────────────────

def test_score_github_issue_good_first_issue():
    issue = {
        "number": 100,
        "title": "Fix typo in README",
        "body": "There is a typo on line 5.",
        "labels": ["good first issue", "documentation"],
        "comments": 1,
        "html_url": "https://github.com/org/repo/issues/100",
    }
    result = score_github_issue(issue)
    assert result["difficulty_tier"] == "beginner"
    assert result["difficulty"] <= 3
    assert result["github_issue_number"] == 100
    assert result["overall_score"] > 0


def test_score_github_issue_security():
    issue = {
        "number": 200,
        "title": "SQL injection vulnerability in query builder",
        "body": "Security risk found.",
        "labels": ["security", "bug"],
        "comments": 8,
        "html_url": "https://github.com/org/repo/issues/200",
    }
    result = score_github_issue(issue)
    assert result["difficulty_tier"] == "advanced"
    assert result["impact"] >= 8
    assert result["category"] in ("security", "bug")


def test_score_code_smell_too_long():
    issue = {
        "file": "app/services/main_service.py",
        "issue": "Function 'process_data' is too long (120 lines)",
    }
    result = score_code_smell(issue)
    assert result["source"] == "ast_analysis"
    assert result["category"] == "refactor"
    assert result["github_issue_number"] is None
    assert result["overall_score"] > 0


def test_score_all_opportunities_returns_structure():
    github_issues = [
        {
            "number": 1, "title": "Fix bug", "body": "A bug",
            "labels": ["bug"], "comments": 2,
            "html_url": "https://github.com/org/repo/issues/1"
        },
        {
            "number": 2, "title": "Add feature", "body": "A feature",
            "labels": ["good first issue"], "comments": 5,
            "html_url": "https://github.com/org/repo/issues/2"
        },
    ]
    ast_issues = [
        {"file": "app/main.py", "issue": "Function 'run' is too long (60 lines)"}
    ]
    result = score_all_opportunities(github_issues, ast_issues)

    assert "all" in result
    assert "beginner" in result
    assert "intermediate" in result
    assert "advanced" in result
    assert result["total_count"] == 3
    assert len(result["all"]) == 3


def test_opportunities_sorted_by_score():
    github_issues = [
        {
            "number": 1, "title": "Fix typo", "body": "",
            "labels": ["good first issue"], "comments": 0,
            "html_url": "https://github.com/org/repo/issues/1"
        },
        {
            "number": 2, "title": "Security vulnerability", "body": "",
            "labels": ["security"], "comments": 10,
            "html_url": "https://github.com/org/repo/issues/2"
        },
    ]
    result = score_all_opportunities(github_issues, [])
    scores = [o["overall_score"] for o in result["all"]]
    assert scores == sorted(scores, reverse=True)


def test_max_total_cap():
    issues = [
        {
            "number": i, "title": f"Issue {i}", "body": "",
            "labels": ["bug"], "comments": 1,
            "html_url": f"https://github.com/org/repo/issues/{i}"
        }
        for i in range(50)
    ]
    result = score_all_opportunities(issues, [], max_total=10)
    assert result["total_count"] == 10
```

---

## Validation Checklist

[ ] backend/app/services/scoring_engine.py created with all functions
[ ] backend/tests/test_scoring_engine.py created
[ ] All 18 tests pass: pytest backend/tests/test_scoring_engine.py
[ ] No Docker rebuild needed (no new packages)
[ ] Manual verification in Python shell:

    from app.services.scoring_engine import score_all_opportunities

    issues = [
        {"number": 1, "title": "Fix login bug", "body": "Users can't login",
         "labels": ["bug"], "comments": 3,
         "html_url": "https://github.com/org/repo/issues/1"},
        {"number": 2, "title": "Add dark mode", "body": "Feature request",
         "labels": ["good first issue", "enhancement"], "comments": 8,
         "html_url": "https://github.com/org/repo/issues/2"},
    ]
    result = score_all_opportunities(issues, [])
    print(result["total_count"])       # 2
    print(result["all"][0]["title"])   # highest scored first
    print(result["beginner"])          # good first issue should be here

[ ] Good first issue appears in beginner list
[ ] Results sorted highest score first

---

## What Part 8 Will Cover

- Matching algorithm (user profile vs opportunities)
- Suitability score per user per opportunity
- User profile schema (Pydantic model, no DB yet)

Do NOT add matching in Part 7.
Do NOT add database writes in Part 7.

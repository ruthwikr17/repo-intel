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
    """
    Realistic estimates for developers using AI tools.
    In 2026, most tasks take 30 min - 2 hours with AI assistance.
    """
    base_hours = {
        1: 1,  # trivial: 1 hour
        2: 1,  # very easy: 1 hour
        3: 1,  # easy: 1 hour
        4: 2,  # moderate: 2 hours
        5: 2,  # medium: 2 hours
        6: 3,  # medium-hard: 3 hours
        7: 4,  # hard: 4 hours
        8: 6,  # very hard: 6 hours
        9: 8,  # expert: 8 hours
        10: 12,  # extreme: 12 hours
    }
    hours = base_hours.get(difficulty, 2)
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


def calculate_score(
    impact: int, learning: int, feasibility: int, difficulty: int
) -> float:
    """
    Core scoring formula:
    Score = (Impact x Learning x Feasibility) - Difficulty
    Higher score = better opportunity.
    """
    return (impact * learning * feasibility) - difficulty


# ─── Score GitHub Issues ──────────────────────────────────────────────────────


def score_github_issue(issue: dict) -> dict:
    labels = issue.get("labels", [])
    title = issue.get("title", "").lower()
    body = (issue.get("body") or "").lower()
    comments = issue.get("comments", 0)

    # Detect category more accurately
    category = detect_category_from_labels(labels, title)

    # Difficulty: smarter detection
    difficulty = get_difficulty_from_labels(labels)

    # Refine difficulty from title keywords
    if any(w in title for w in ["refactor", "redesign", "rewrite", "migrate"]):
        difficulty = max(difficulty, 7)
    elif any(w in title for w in ["add", "implement", "create", "build"]):
        difficulty = max(difficulty, 5)
    elif any(w in title for w in ["fix", "bug", "error", "crash", "broken"]):
        difficulty = max(difficulty, 4)
    elif any(w in title for w in ["typo", "spelling", "docs", "readme", "comment"]):
        difficulty = min(difficulty, 3)
    elif any(w in title for w in ["security", "vulnerability", "auth", "cve"]):
        difficulty = max(difficulty, 8)

    # Impact: based on who is affected
    impact = get_impact_from_labels(labels)
    if any(w in title + body for w in ["crash", "broken", "cannot", "fails", "all users"]):
        impact = min(10, impact + 2)
    if any(w in title for w in ["docs", "typo", "comment", "readme"]):
        impact = min(impact, 4)
    if any(w in title for w in ["security", "vulnerability", "data loss"]):
        impact = 10

    # Learning value: based on category and complexity
    learning_map = {
        "bug": 6,
        "feature": 8,
        "documentation": 3,
        "refactor": 7,
        "performance": 9,
        "security": 9,
        "testing": 5,
        "dependency": 3,
    }
    learning = learning_map.get(category, 5)

    # Feasibility: more comments = more documented = easier
    if comments >= 10:
        feasibility = 9
    elif comments >= 5:
        feasibility = 7
    elif comments >= 2:
        feasibility = 6
    else:
        feasibility = 4

    labels_lower = [l.lower() for l in labels]
    if "good first issue" in labels_lower or "good-first-issue" in labels_lower:
        feasibility = min(10, feasibility + 2)
        difficulty = min(difficulty, 3)

    difficulty = clamp(difficulty)
    impact = clamp(impact)
    learning = clamp(learning)
    feasibility = clamp(feasibility)

    hours = estimate_hours(difficulty, category)
    tier = assign_difficulty_tier(difficulty, hours)
    score = calculate_score(impact, learning, feasibility, difficulty)

    return {
        "title": issue.get("title", ""),
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

    impact = 5  # code quality improvements are medium impact
    learning = 6  # refactoring teaches good patterns
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
    description = (
        f"Code quality issue detected in {file_path}: {issue.get('issue', '')}"
    )

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
    ai_suggestions: list[dict] = None,
    max_total: int = 30,
) -> dict:
    """
    Score all opportunities from both sources.
    Returns sorted lists by tier and overall ranking.

    Input:
      - github_issues: list of issues from GitHub API
      - ast_issues: list of issues from AST analysis
      - ai_suggestions: list of AI-generated suggestions (optional)
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

    # Add AI-generated suggestions
    if ai_suggestions:
        for suggestion in ai_suggestions:
            try:
                # Convert minutes to hours for display
                minutes = suggestion.get("estimated_minutes", 60)
                hours = max(1, round(minutes / 60))

                scored.append(
                    {
                        "title": suggestion.get("title", "")[:255],
                        "description": suggestion.get("description", "")[:300],
                        "category": suggestion.get("category", "feature"),
                        "source": "ai_suggestion",
                        "github_issue_number": suggestion.get("github_issue_number"),
                        "github_issue_url": suggestion.get("github_issue_url"),
                        "difficulty": suggestion.get("difficulty", 5),
                        "impact": suggestion.get("impact", 6),
                        "learning_value": suggestion.get("learning_value", 6),
                        "feasibility": 7,
                        "overall_score": calculate_score(
                            suggestion.get("impact", 6),
                            suggestion.get("learning_value", 6),
                            7,
                            suggestion.get("difficulty", 5),
                        ),
                        "estimated_hours": hours,
                        "difficulty_tier": suggestion.get(
                            "difficulty_tier", "intermediate"
                        ),
                    }
                )
            except Exception:
                continue

    # Deduplicate by title (fix for duplicate opportunities bug)
    seen_titles = set()
    unique_scored = []
    for opp in scored:
        title = opp.get("title", "").lower().strip()
        if title not in seen_titles:
            seen_titles.add(title)
            unique_scored.append(opp)

    # Sort by overall_score descending
    unique_scored.sort(key=lambda x: x["overall_score"], reverse=True)
    unique_scored = unique_scored[:max_total]

    beginner = [o for o in unique_scored if o["difficulty_tier"] == "beginner"]
    intermediate = [o for o in unique_scored if o["difficulty_tier"] == "intermediate"]
    advanced = [o for o in unique_scored if o["difficulty_tier"] == "advanced"]

    return {
        "all": unique_scored,
        "beginner": beginner,
        "intermediate": intermediate,
        "advanced": advanced,
        "total_count": len(unique_scored),
        "beginner_count": len(beginner),
        "intermediate_count": len(intermediate),
        "advanced_count": len(advanced),
    }

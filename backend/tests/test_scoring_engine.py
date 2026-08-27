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

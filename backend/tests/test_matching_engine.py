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

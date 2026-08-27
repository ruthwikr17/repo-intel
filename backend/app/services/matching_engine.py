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

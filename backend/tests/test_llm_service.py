from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_service import run_llm_analysis
from app.services.prompts import (
    prompt_architecture,
    prompt_project_summary,
    prompt_setup_guide,
)

SAMPLE_REPO_DATA = {
    "metadata": {
        "full_name": "psf/requests",
        "description": "A simple HTTP library",
        "stars": 54000,
        "forks": 10000,
        "open_issues_count": 200,
        "language": "Python",
        "license": "Apache 2.0",
        "topics": ["http", "python"],
    },
    "issues": [{"number": 100, "title": "Fix timeout bug", "comments": 3}],
    "languages": {"Python": 390000},
    "tech_stack": {
        "frameworks": ["pytest"],
        "has_tests": True,
        "has_docker": False,
        "has_ci": True,
        "manifests_found": ["requirements.txt"],
    },
    "directory_structure": {
        "name": "requests",
        "type": "dir",
        "children": [{"name": "src", "type": "dir", "children": []}],
    },
    "ast_analysis": {
        "files_analyzed": 10,
        "avg_complexity": 4.2,
        "total_functions": 45,
        "total_classes": 8,
        "all_issues": [],
        "all_imports": ["os", "sys", "json"],
        "file_results": {},
    },
}


def test_prompt_project_summary_contains_repo_name():
    prompt = prompt_project_summary(SAMPLE_REPO_DATA)
    assert "psf/requests" in prompt
    assert "54" in prompt  # stars


def test_prompt_setup_guide_contains_language():
    prompt = prompt_setup_guide(SAMPLE_REPO_DATA)
    assert "Python" in prompt


def test_prompt_architecture_contains_metrics():
    prompt = prompt_architecture(SAMPLE_REPO_DATA)
    assert "10" in prompt  # files_analyzed
    assert "4.2" in prompt  # avg_complexity


@pytest.mark.asyncio
async def test_run_llm_analysis_tier2_returns_all_keys():
    """Test Tier 2 (all Groq) returns correct structure."""
    with patch(
        "app.services.llm_service.call_groq",
        new_callable=AsyncMock,
        return_value="Mocked LLM response",
    ):
        result = await run_llm_analysis(SAMPLE_REPO_DATA, gemini_key=None)

    assert result["quality_tier"] == "MEDIUM"
    assert "groq-llama-3.3" in result["apis_used"]
    assert "summary" in result
    assert "architecture_explanation" in result
    assert "setup_guide" in result
    assert "code_walkthrough" in result
    assert "common_patterns" in result
    assert "executive_summary" in result
    assert "code_quality_report" in result
    assert "contributor_guide_narrative" in result


@pytest.mark.asyncio
async def test_run_llm_analysis_tier1_uses_gemini():
    """Test Tier 1 (hybrid) returns HIGH quality tier."""
    with (
        patch(
            "app.services.llm_service.call_groq",
            new_callable=AsyncMock,
            return_value="Groq response",
        ),
        patch(
            "app.services.llm_service.call_gemini",
            new_callable=AsyncMock,
            return_value="Gemini response",
        ),
    ):
        result = await run_llm_analysis(SAMPLE_REPO_DATA, gemini_key="fake-key")

    assert result["quality_tier"] == "HIGH"
    assert "gemini-3.6-flash" in result["apis_used"]
    assert result["summary"] == "Groq response"
    assert result["architecture_explanation"] == "Gemini response"

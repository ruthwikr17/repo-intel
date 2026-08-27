# CONTEXT FILE: Part 5 - LLM Integration (Gemini 2.5 Pro + Groq Llama 3.3)
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-4

- Part 1: FastAPI, Docker, PostgreSQL, Redis
- Part 2: GitHub API service (fetch_full_repo_data)
- Part 3: Repo cloning, AST analysis (analyze_repository_locally)
- Part 4: Full database models, Alembic setup, auto table creation

---

## What Part 5 Builds

LLM service that:
- Makes 8 parallel LLM calls per repository analysis
- Uses Gemini 2.5 Pro for 4 complex reasoning tasks
- Uses Groq Llama 3.3 for 4 structured generation tasks
- Returns all results as a structured dict

New packages needed - add to backend/requirements.txt:
- google-generativeai==0.7.2
- groq==0.9.0

---

## Files to Create

- backend/app/services/llm_service.py     (NEW - main file for this part)
- backend/app/services/prompts.py         (NEW - all prompt templates)
- backend/tests/test_llm_service.py       (NEW - tests)

Do NOT modify any other files in this part.

---

## Prompt Templates

### backend/app/services/prompts.py

These are the exact prompts used for each LLM call.
Do not shorten or simplify them.

```python
# All 8 prompt templates for RepoInsight LLM calls.
# Each function takes repo_data dict and returns a formatted string.
# repo_data contains: metadata, issues, languages, commits,
#                     tech_stack, directory_structure, ast_analysis


def prompt_project_summary(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    languages = repo_data.get("languages", {})
    tech_stack = repo_data.get("tech_stack", {})
    top_issues = repo_data.get("issues", [])[:5]

    issues_text = "\n".join(
        f"- #{i['number']}: {i['title']}" for i in top_issues
    ) or "No open issues"

    lang_text = ", ".join(languages.keys()) if languages else "Unknown"
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "None detected"

    return f"""You are an expert open source analyst. Write a clear, engaging project summary.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', 'No description')}
STARS: {metadata.get('stars', 0):,}
LANGUAGES: {lang_text}
FRAMEWORKS: {frameworks}
LICENSE: {metadata.get('license', 'Unknown')}
TOPICS: {', '.join(metadata.get('topics', []))}

SAMPLE OPEN ISSUES:
{issues_text}

Write 3 paragraphs:
1. What this project does and its main purpose (2-3 sentences)
2. Who uses it, what companies or communities rely on it (2-3 sentences)
3. Why it matters in the ecosystem and what problems it solves (2-3 sentences)

Be specific, factual, and avoid generic statements.
Do not use bullet points. Write flowing prose only.
Total length: 200-300 words."""


def prompt_architecture(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    structure = repo_data.get("directory_structure", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})

    imports = ast.get("all_imports", [])[:20]
    files_count = ast.get("files_analyzed", 0)
    avg_complexity = ast.get("avg_complexity", 0)
    total_functions = ast.get("total_functions", 0)
    total_classes = ast.get("total_classes", 0)

    structure_summary = []
    if isinstance(structure, dict) and "children" in structure:
        for child in structure.get("children", [])[:10]:
            structure_summary.append(f"- {child.get('name', '')}/")

    return f"""You are a senior software architect analyzing a GitHub repository.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
LANGUAGE: {metadata.get('language', 'Unknown')}
FRAMEWORKS: {', '.join(tech_stack.get('frameworks', []))}

DIRECTORY STRUCTURE (top level):
{chr(10).join(structure_summary) or 'Not available'}

CODE METRICS:
- Files analyzed: {files_count}
- Total functions: {total_functions}
- Total classes: {total_classes}
- Average cyclomatic complexity: {avg_complexity}
- Key imports/dependencies: {', '.join(imports[:15])}

HAS TESTS: {tech_stack.get('has_tests', False)}
HAS DOCKER: {tech_stack.get('has_docker', False)}
HAS CI: {tech_stack.get('has_ci', False)}

Provide a detailed architecture explanation covering:
1. How the codebase is organized (module structure)
2. Key components and what each is responsible for
3. How data flows through the system
4. Design patterns used
5. How a new contributor should navigate the codebase

Length: 300-400 words. Use clear section headings."""


def prompt_code_walkthrough(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    file_results = ast.get("file_results", {})

    # Pick up to 5 most important files
    important_files = list(file_results.keys())[:5]
    files_summary = []
    for f in important_files:
        data = file_results[f]
        funcs = [fn["name"] for fn in data.get("functions", [])[:5]]
        classes = data.get("classes", [])[:3]
        files_summary.append(
            f"File: {f}\n  Classes: {', '.join(classes) or 'none'}\n"
            f"  Functions: {', '.join(funcs) or 'none'}"
        )

    return f"""You are an expert developer explaining a codebase to a new contributor.

REPOSITORY: {metadata.get('full_name', 'Unknown')}

KEY FILES FOUND:
{chr(10).join(files_summary) or 'No Python files analyzed'}

Write a code walkthrough explaining:
1. The entry point of the application and how it starts
2. What each key file does and why it exists
3. How the main classes and functions relate to each other
4. Where a new contributor should look first
5. Which files they will likely need to modify for common tasks

Length: 300-400 words. Be specific about file names and function names.
Use a friendly, mentoring tone."""


def prompt_patterns_and_gotchas(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    tech_stack = repo_data.get("tech_stack", {})
    issues_list = ast.get("all_issues", [])[:10]

    issues_text = "\n".join(
        f"- [{i['file']}] {i['issue']}" for i in issues_list
    ) or "No issues detected"

    frameworks = tech_stack.get("frameworks", [])

    return f"""You are a senior developer who has worked extensively with this codebase.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
FRAMEWORKS: {', '.join(frameworks)}

CODE QUALITY ISSUES DETECTED:
{issues_text}

Write two sections:

## Common Patterns
Describe 4-5 recurring patterns, conventions, and practices used in this codebase.
Include: naming conventions, error handling approach, testing patterns, code style.

## Gotchas and Tips
List 4-5 specific things a new contributor must know before submitting a PR:
- Common mistakes that get PRs rejected
- Non-obvious requirements
- Testing expectations
- Performance or security considerations specific to this project

Length: 300-400 words total. Be specific and actionable."""


def prompt_setup_guide(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    languages = repo_data.get("languages", {})

    manifests = tech_stack.get("manifests_found", [])
    has_docker = tech_stack.get("has_docker", False)
    has_tests = tech_stack.get("has_tests", False)
    frameworks = tech_stack.get("frameworks", [])
    lang = metadata.get("language", "Unknown")

    return f"""You are a developer advocate writing a setup guide for new contributors.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
PRIMARY LANGUAGE: {lang}
FRAMEWORKS: {', '.join(frameworks)}
MANIFEST FILES: {', '.join(manifests)}
HAS DOCKER: {has_docker}
HAS TESTS: {has_tests}

Write a step-by-step setup guide with exactly these sections:

## Prerequisites
List what must be installed before starting (language runtime, tools, etc.)

## Clone and Setup
Exact terminal commands to:
1. Fork the repo on GitHub
2. Clone the fork locally
3. Install dependencies
4. Set up environment variables (if needed)

## Verify Setup
Commands to run to confirm setup worked correctly.

## Running Tests
Exact command to run the test suite locally.

## Before You Code
2-3 things to read or understand before making any changes.

Use exact terminal commands where possible.
Length: 250-350 words."""


def prompt_contributor_guide_narrative(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    issues = repo_data.get("issues", [])[:3]

    issues_text = "\n".join(
        f"- #{i['number']}: {i['title']} ({i['comments']} comments)"
        for i in issues
    ) or "No issues available"

    return f"""You are writing the introduction and narrative sections of a contributor guide PDF.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', '')}
STARS: {metadata.get('stars', 0):,}

SAMPLE OPEN ISSUES:
{issues_text}

Write three narrative sections for the PDF:

## Why Contribute to This Project
2 paragraphs on the value of contributing: career impact, learning opportunities,
community impact. Be motivating and specific to this project.

## What Kind of Contributions Are Welcome
1 paragraph describing the types of contributions maintainers typically welcome
based on the project type and open issues.

## How to Get Help
1 paragraph advising new contributors on how to ask questions, where to discuss
ideas before coding, and how to communicate with maintainers.

Total length: 200-250 words. Friendly, encouraging tone."""


def prompt_executive_summary(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    issues = repo_data.get("issues", [])

    avg_complexity = ast.get("avg_complexity", 0)
    has_tests = tech_stack.get("has_tests", False)
    has_ci = tech_stack.get("has_ci", False)

    return f"""You are writing a one-page executive summary for a technical decision maker.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', '')}
STARS: {metadata.get('stars', 0):,}
FORKS: {metadata.get('forks', 0):,}
OPEN ISSUES: {metadata.get('open_issues_count', 0)}
LANGUAGE: {metadata.get('language', 'Unknown')}
LICENSE: {metadata.get('license', 'Unknown')}
HAS TESTS: {has_tests}
HAS CI: {has_ci}
AVG CODE COMPLEXITY: {avg_complexity}
TOTAL ISSUES IN SAMPLE: {len(issues)}

Write a concise executive summary with exactly these sections:

## Overall Assessment
One sentence verdict: ADOPT / EVALUATE / AVOID with one-line reason.

## Strengths
3 bullet points (one line each)

## Risks
3 bullet points (one line each)

## Recommendation
2-3 sentences on what the decision maker should do next.

Total length: 150-200 words. Business language, no jargon."""


def prompt_code_quality_report(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    tech_stack = repo_data.get("tech_stack", {})

    all_issues = ast.get("all_issues", [])[:15]
    avg_complexity = ast.get("avg_complexity", 0)
    files_analyzed = ast.get("files_analyzed", 0)
    total_functions = ast.get("total_functions", 0)
    total_classes = ast.get("total_classes", 0)

    issues_text = "\n".join(
        f"- [{i['file']}] {i['issue']}" for i in all_issues
    ) or "No issues detected"

    return f"""You are a senior code reviewer writing a code quality assessment report.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
FILES ANALYZED: {files_analyzed}
TOTAL FUNCTIONS: {total_functions}
TOTAL CLASSES: {total_classes}
AVERAGE CYCLOMATIC COMPLEXITY: {avg_complexity}
HAS TESTS: {tech_stack.get('has_tests', False)}
HAS CI: {tech_stack.get('has_ci', False)}

DETECTED CODE ISSUES:
{issues_text}

Write a professional code quality report with these sections:

## Quality Score
Give an overall score out of 10 with a one-line justification.

## Complexity Analysis
Interpret the complexity metrics. Is this high or low for this type of project?
What does it mean for maintainability?

## Issues Found
Summarize the detected issues by category. What patterns do you see?

## Recommendations
3-4 specific, actionable recommendations to improve code quality.

## Maintenance Risk
Low / Medium / High with explanation.

Length: 300-400 words. Professional, technical tone."""
```

---

## LLM Service

### backend/app/services/llm_service.py

```python
import asyncio
import google.generativeai as genai
from groq import AsyncGroq
from app.config import get_settings
from app.services.prompts import (
    prompt_project_summary,
    prompt_architecture,
    prompt_code_walkthrough,
    prompt_patterns_and_gotchas,
    prompt_setup_guide,
    prompt_contributor_guide_narrative,
    prompt_executive_summary,
    prompt_code_quality_report,
)

settings = get_settings()


# ─── Gemini Client ────────────────────────────────────────────────────────────

def get_gemini_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        )
    )


async def call_gemini(prompt: str, api_key: str) -> str:
    """Call Gemini API with given prompt and API key."""
    try:
        model = get_gemini_model(api_key)
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error: {str(e)}]"


# ─── Groq Client ─────────────────────────────────────────────────────────────

async def call_groq(prompt: str) -> str:
    """Call Groq Llama API with given prompt."""
    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Groq Error: {str(e)}]"


# ─── Tier 1: Hybrid (Gemini + Groq) ─────────────────────────────────────────

async def run_tier1_analysis(repo_data: dict, gemini_key: str) -> dict:
    """
    Tier 1: High quality hybrid.
    Gemini handles 4 complex reasoning tasks.
    Groq handles 4 structured generation tasks.
    All 8 run in parallel via asyncio.gather.
    """
    (
        summary,
        architecture,
        walkthrough,
        quality_report,
        setup_guide,
        contributor_narrative,
        executive_summary,
        patterns_gotchas,
    ) = await asyncio.gather(
        call_groq(prompt_project_summary(repo_data)),
        call_gemini(prompt_architecture(repo_data), gemini_key),
        call_gemini(prompt_code_walkthrough(repo_data), gemini_key),
        call_gemini(prompt_code_quality_report(repo_data), gemini_key),
        call_groq(prompt_setup_guide(repo_data)),
        call_groq(prompt_contributor_guide_narrative(repo_data)),
        call_groq(prompt_executive_summary(repo_data)),
        call_gemini(prompt_patterns_and_gotchas(repo_data), gemini_key),
    )

    return {
        "quality_tier": "HIGH",
        "apis_used": ["gemini-3.6-flash", "groq-llama-3.3"],
        "summary": summary,
        "architecture_explanation": architecture,
        "code_walkthrough": walkthrough,
        "code_quality_report": quality_report,
        "setup_guide": setup_guide,
        "contributor_guide_narrative": contributor_narrative,
        "executive_summary": executive_summary,
        "common_patterns": patterns_gotchas,
    }


# ─── Tier 2: Groq Only ───────────────────────────────────────────────────────

async def run_tier2_analysis(repo_data: dict) -> dict:
    """
    Tier 2: All Groq fallback.
    Used when both Gemini projects are exhausted.
    Same prompts, all sent to Groq.
    """
    (
        summary,
        architecture,
        walkthrough,
        quality_report,
        setup_guide,
        contributor_narrative,
        executive_summary,
        patterns_gotchas,
    ) = await asyncio.gather(
        call_groq(prompt_project_summary(repo_data)),
        call_groq(prompt_architecture(repo_data)),
        call_groq(prompt_code_walkthrough(repo_data)),
        call_groq(prompt_code_quality_report(repo_data)),
        call_groq(prompt_setup_guide(repo_data)),
        call_groq(prompt_contributor_guide_narrative(repo_data)),
        call_groq(prompt_executive_summary(repo_data)),
        call_groq(prompt_patterns_and_gotchas(repo_data)),
    )

    return {
        "quality_tier": "MEDIUM",
        "apis_used": ["groq-llama-3.3"],
        "summary": summary,
        "architecture_explanation": architecture,
        "code_walkthrough": walkthrough,
        "code_quality_report": quality_report,
        "setup_guide": setup_guide,
        "contributor_guide_narrative": contributor_narrative,
        "executive_summary": executive_summary,
        "common_patterns": patterns_gotchas,
    }


# ─── Master LLM Analysis ─────────────────────────────────────────────────────

async def run_llm_analysis(repo_data: dict, gemini_key: str | None = None) -> dict:
    """
    Master function called by other services.
    If gemini_key is provided: runs Tier 1 (hybrid).
    If gemini_key is None: runs Tier 2 (Groq only).
    """
    if gemini_key:
        return await run_tier1_analysis(repo_data, gemini_key)
    else:
        return await run_tier2_analysis(repo_data)
```

---

## Tests

### backend/tests/test_llm_service.py

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.llm_service import run_llm_analysis
from app.services.prompts import (
    prompt_project_summary,
    prompt_setup_guide,
    prompt_architecture,
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
    "issues": [
        {"number": 100, "title": "Fix timeout bug", "comments": 3}
    ],
    "languages": {"Python": 390000},
    "tech_stack": {
        "frameworks": ["pytest"],
        "has_tests": True,
        "has_docker": False,
        "has_ci": True,
        "manifests_found": ["requirements.txt"]
    },
    "directory_structure": {
        "name": "requests",
        "type": "dir",
        "children": [{"name": "src", "type": "dir", "children": []}]
    },
    "ast_analysis": {
        "files_analyzed": 10,
        "avg_complexity": 4.2,
        "total_functions": 45,
        "total_classes": 8,
        "all_issues": [],
        "all_imports": ["os", "sys", "json"],
        "file_results": {}
    }
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
        return_value="Mocked LLM response"
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
    with patch(
        "app.services.llm_service.call_groq",
        new_callable=AsyncMock,
        return_value="Groq response"
    ), patch(
        "app.services.llm_service.call_gemini",
        new_callable=AsyncMock,
        return_value="Gemini response"
    ):
        result = await run_llm_analysis(SAMPLE_REPO_DATA, gemini_key="fake-key")

    assert result["quality_tier"] == "HIGH"
    assert "gemini-3.6-flash" in result["apis_used"]
    assert result["summary"] == "Groq response"
    assert result["architecture_explanation"] == "Gemini response"
```

---

## Validation Checklist

[ ] google-generativeai and groq added to requirements.txt
[ ] backend/app/services/prompts.py created with all 8 prompt functions
[ ] backend/app/services/llm_service.py created with all functions
[ ] All 5 tests pass: pytest backend/tests/test_llm_service.py
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d
[ ] Manual test (uses real API keys, costs quota):

In Python shell inside backend container:
    import asyncio
    from app.services.llm_service import run_llm_analysis

    sample = {
        "metadata": {"full_name": "psf/requests", "description": "HTTP lib",
                     "stars": 54000, "forks": 10000, "open_issues_count": 200,
                     "language": "Python", "license": "Apache", "topics": []},
        "issues": [], "languages": {"Python": 390000},
        "tech_stack": {"frameworks": [], "has_tests": True,
                       "has_docker": False, "has_ci": True, "manifests_found": []},
        "directory_structure": {}, "ast_analysis": {"files_analyzed": 5,
        "avg_complexity": 4.0, "total_functions": 20, "total_classes": 3,
        "all_issues": [], "all_imports": [], "file_results": {}}
    }

    result = asyncio.run(run_llm_analysis(sample, gemini_key=None))
    print(result["quality_tier"])
    print(result["summary"][:200])

[ ] summary field contains real LLM-generated text (not error message)
[ ] All 8 keys present in result

---

## Important Notes

- gemini-3.6-flash is used instead of gemini-3.6-flash in code
  because flash is available on free tier. The model string can be
  updated to gemini-3.6-flash when Pro is available on your account.

- Tier 1 uses Groq for summary, setup_guide, contributor_narrative,
  executive_summary and Gemini for architecture, walkthrough,
  patterns_gotchas, quality_report.

- Tests use mocks so they do not consume real API quota.

---

## What Part 6 Will Cover

- Quota Monitor: tracks Gemini and Groq usage per day
- Tier Selection: automatically picks Tier 1 or Tier 2
- Stores all API calls in api_logs table

Do NOT add quota monitoring in Part 5.
Do NOT add database writes in Part 5.

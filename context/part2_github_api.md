# CONTEXT FILE: Part 2 - GitHub API Integration
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Part 1

- FastAPI app running on port 8000
- PostgreSQL connected and healthy
- Redis connected and healthy
- Health endpoint: GET /api/health
- Folder structure with backend/app/services/ and backend/app/utils/

---

## What Part 2 Builds

A GitHub API service that fetches all raw data needed for repository analysis.

Files to create or modify:
- backend/app/services/github_service.py   (NEW - main file for this part)
- backend/app/utils/validators.py          (NEW - URL validation)
- backend/app/routes/repos.py              (NEW - one endpoint only)
- backend/app/main.py                      (MODIFY - add repos router)
- backend/tests/test_github_service.py     (NEW - tests)

---

## GitHub API Service

### backend/app/services/github_service.py

This service fetches repository data from GitHub REST API v3.
Uses httpx for async HTTP calls.
Uses personal access token from settings for authentication (5,000 req/hr).

Functions to implement:

1. parse_repo_url(url: str) -> tuple[str, str]
   - Input: "https://github.com/django/django-rest-framework"
   - Output: ("django", "django-rest-framework")
   - Raise ValueError if URL is not a valid GitHub repo URL

2. get_repo_metadata(owner: str, repo: str) -> dict
   - Calls: GET https://api.github.com/repos/{owner}/{repo}
   - Returns: name, full_name, description, stars, forks, open_issues_count,
              language, created_at, updated_at, default_branch, license,
              has_issues, has_wiki, topics, html_url
   - Raise httpx.HTTPStatusError on failure

3. get_repo_issues(owner: str, repo: str, max_issues: int = 50) -> list[dict]
   - Calls: GET https://api.github.com/repos/{owner}/{repo}/issues
   - Params: state=open, per_page=50, sort=created, direction=desc
   - Filters out pull requests (issues with "pull_request" key)
   - Returns list of: number, title, body, labels (names only),
                      state, created_at, comments, html_url
   - Handle pagination: fetch up to max_issues only

4. get_repo_contributors(owner: str, repo: str, max: int = 10) -> list[dict]
   - Calls: GET https://api.github.com/repos/{owner}/{repo}/contributors
   - Returns: login, contributions, html_url
   - Returns top max contributors only

5. get_repo_languages(owner: str, repo: str) -> dict
   - Calls: GET https://api.github.com/repos/{owner}/{repo}/languages
   - Returns: {"Python": 12345, "JavaScript": 6789}

6. get_repo_commits(owner: str, repo: str, max: int = 30) -> list[dict]
   - Calls: GET https://api.github.com/repos/{owner}/{repo}/commits
   - Params: per_page=30
   - Returns: sha (first 7 chars), message (first line only),
              author_name, author_date
   - Returns up to max commits only

7. fetch_full_repo_data(url: str) -> dict
   - Master function that calls all above functions
   - Calls parse_repo_url first
   - Calls all 5 fetch functions concurrently using asyncio.gather
   - Returns combined dict with keys:
     metadata, issues, contributors, languages, commits
   - This is the main function called by other parts of the app

### Full implementation:

```python
import httpx
import asyncio
import re
from app.config import get_settings

settings = get_settings()

GITHUB_API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def parse_repo_url(url: str) -> tuple[str, str]:
    pattern = r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$"
    match = re.match(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub repository URL: {url}")
    return match.group(1), match.group(2)


async def get_repo_metadata(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")
        response.raise_for_status()
        data = response.json()
        return {
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description", ""),
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues_count": data["open_issues_count"],
            "language": data.get("language", ""),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "default_branch": data["default_branch"],
            "license": data["license"]["name"] if data.get("license") else None,
            "topics": data.get("topics", []),
            "html_url": data["html_url"],
            "has_issues": data["has_issues"],
        }


async def get_repo_issues(owner: str, repo: str, max_issues: int = 50) -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
            params={"state": "open", "per_page": min(max_issues, 50),
                    "sort": "created", "direction": "desc"}
        )
        response.raise_for_status()
        issues = []
        for item in response.json():
            if "pull_request" in item:
                continue
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "body": (item.get("body") or "")[:500],
                "labels": [l["name"] for l in item.get("labels", [])],
                "state": item["state"],
                "created_at": item["created_at"],
                "comments": item["comments"],
                "html_url": item["html_url"],
            })
        return issues[:max_issues]


async def get_repo_contributors(owner: str, repo: str, max: int = 10) -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
            params={"per_page": max}
        )
        response.raise_for_status()
        return [
            {
                "login": c["login"],
                "contributions": c["contributions"],
                "html_url": c["html_url"]
            }
            for c in response.json()[:max]
        ]


async def get_repo_languages(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
        )
        response.raise_for_status()
        return response.json()


async def get_repo_commits(owner: str, repo: str, max: int = 30) -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": max}
        )
        response.raise_for_status()
        commits = []
        for c in response.json()[:max]:
            message = c["commit"]["message"].split("\n")[0]
            commits.append({
                "sha": c["sha"][:7],
                "message": message[:100],
                "author_name": c["commit"]["author"]["name"],
                "author_date": c["commit"]["author"]["date"],
            })
        return commits


async def fetch_full_repo_data(url: str) -> dict:
    owner, repo = parse_repo_url(url)
    metadata, issues, contributors, languages, commits = await asyncio.gather(
        get_repo_metadata(owner, repo),
        get_repo_issues(owner, repo),
        get_repo_contributors(owner, repo),
        get_repo_languages(owner, repo),
        get_repo_commits(owner, repo),
    )
    return {
        "owner": owner,
        "repo": repo,
        "metadata": metadata,
        "issues": issues,
        "contributors": contributors,
        "languages": languages,
        "commits": commits,
    }
```

---

## URL Validator

### backend/app/utils/validators.py

```python
import re

def is_valid_github_url(url: str) -> bool:
    pattern = r"https?://github\.com/[^/]+/[^/]+"
    return bool(re.match(pattern, url.strip()))
```

---

## Route

### backend/app/routes/repos.py

One endpoint only in this part: POST /api/repos/fetch-raw
This endpoint fetches raw GitHub data and returns it as JSON.
No database storage yet. No LLM calls. Raw data only.

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.github_service import fetch_full_repo_data
from app.utils.validators import is_valid_github_url

router = APIRouter()

class RepoURLRequest(BaseModel):
    url: str

@router.post("/repos/fetch-raw")
async def fetch_raw_repo_data(request: RepoURLRequest):
    if not is_valid_github_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    try:
        data = await fetch_full_repo_data(request.url)
        return {"status": "success", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
```

---

## Modify main.py

Add the repos router. Add this import and include_router call:

```python
from app.routes.repos import router as repos_router
app.include_router(repos_router, prefix="/api", tags=["repos"])
```

---

## Tests

### backend/tests/test_github_service.py

```python
import pytest
from app.services.github_service import parse_repo_url
from app.utils.validators import is_valid_github_url

def test_parse_valid_url():
    owner, repo = parse_repo_url("https://github.com/django/django-rest-framework")
    assert owner == "django"
    assert repo == "django-rest-framework"

def test_parse_url_with_trailing_slash():
    owner, repo = parse_repo_url("https://github.com/pallets/flask/")
    assert owner == "pallets"
    assert repo == "flask"

def test_parse_url_with_dot_git():
    owner, repo = parse_repo_url("https://github.com/psf/requests.git")
    assert owner == "psf"
    assert repo == "requests"

def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_repo_url("https://gitlab.com/user/repo")

def test_parse_non_url_raises():
    with pytest.raises(ValueError):
        parse_repo_url("not-a-url")

def test_validator_valid_url():
    assert is_valid_github_url("https://github.com/django/django") is True

def test_validator_invalid_url():
    assert is_valid_github_url("https://gitlab.com/user/repo") is False

def test_validator_empty_string():
    assert is_valid_github_url("") is False
```

---

## Validation Checklist

After building, verify all of these:

[ ] backend/app/services/github_service.py exists with all 7 functions
[ ] backend/app/utils/validators.py exists with is_valid_github_url
[ ] backend/app/routes/repos.py exists with POST /api/repos/fetch-raw
[ ] backend/app/main.py includes repos_router
[ ] backend/tests/test_github_service.py exists with 8 tests
[ ] All 7 unit tests pass: pytest backend/tests/test_github_service.py
[ ] API endpoint works: POST http://localhost:8000/api/repos/fetch-raw
    with body {"url": "https://github.com/psf/requests"}
    returns status: success and data with metadata, issues, contributors, languages, commits
[ ] Invalid URL returns 400 error
[ ] Response includes at least 1 issue from the repo

---

## What Part 3 Will Cover

- Clone repository locally using GitPython
- Walk directory structure
- AST parsing for Python files (complexity, imports)
- Tech stack detection from manifest files

Do NOT build any of this in Part 2.
Do NOT add database storage in Part 2.
Do NOT add LLM calls in Part 2.

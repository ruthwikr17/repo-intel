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



async def get_repo_readme(owner: str, repo: str) -> str:
    """Fetch README content from GitHub API."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
            )
            if response.status_code == 200:
                import base64
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                # Truncate to 3000 chars to avoid token overflow
                return content[:3000]
    except Exception:
        pass
    return ""

async def fetch_full_repo_data(url: str) -> dict:
    owner, repo = parse_repo_url(url)
    metadata, issues, contributors, languages, commits, readme = await asyncio.gather(
        get_repo_metadata(owner, repo),
        get_repo_issues(owner, repo),
        get_repo_contributors(owner, repo),
        get_repo_languages(owner, repo),
        get_repo_commits(owner, repo),
        get_repo_readme(owner, repo),
    )
    return {
        "owner": owner,
        "repo": repo,
        "metadata": metadata,
        "issues": issues,
        "contributors": contributors,
        "languages": languages,
        "commits": commits,
        "readme": readme,
    }

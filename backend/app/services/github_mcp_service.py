"""
GitHub MCP Service
Replaces github_service.py raw REST calls with GitHub MCP Server tool calls.
The LLM uses GitHub tools directly via MCP protocol.
"""

import asyncio
import json
import re
from anthropic import Anthropic
from app.config import get_settings

settings = get_settings()

# GitHub MCP Server URL (official)
GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"

# We use Claude Haiku (cheapest) for MCP tool calls
# These are structured data fetches, not generation tasks
# Cost: ~$0.001 per repository fetch
CLAUDE_MODEL = "claude-haiku-4-5"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from GitHub URL."""
    pattern = r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$"
    match = re.match(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub repository URL: {url}")
    return match.group(1), match.group(2)


async def fetch_repo_data_via_mcp(owner: str, repo: str) -> dict:
    """
    Fetch comprehensive repository data using GitHub MCP Server.
    The LLM calls GitHub tools directly - no manual REST calls needed.
    """
    client = Anthropic()

    prompt = f"""Use the GitHub MCP tools to fetch comprehensive data about {owner}/{repo}.

Call these tools in order:
1. get_repository - get basic repo info (owner: {owner}, repo: {repo})
2. list_issues - get open issues (owner: {owner}, repo: {repo}, state: open, per_page: 50)
3. get_file_contents - get README (owner: {owner}, repo: {repo}, path: README.md)
4. list_commits - get recent commits (owner: {owner}, repo: {repo}, per_page: 30)
5. list_contributors - if available

After fetching all data, return a JSON object with this exact structure:
{{
    "metadata": {{
        "name": "",
        "full_name": "",
        "description": "",
        "stars": 0,
        "forks": 0,
        "open_issues_count": 0,
        "language": "",
        "created_at": "",
        "updated_at": "",
        "default_branch": "",
        "license": null,
        "topics": [],
        "html_url": "",
        "has_issues": true
    }},
    "issues": [
        {{
            "number": 0,
            "title": "",
            "body": "",
            "labels": [],
            "state": "open",
            "created_at": "",
            "comments": 0,
            "html_url": ""
        }}
    ],
    "contributors": [
        {{"login": "", "contributions": 0, "html_url": ""}}
    ],
    "commits": [
        {{"sha": "", "message": "", "author_name": "", "author_date": ""}}
    ],
    "languages": {{}},
    "readme": ""
}}

Return ONLY the JSON. No explanation."""

    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        mcp_servers=[
            {
                "type": "url",
                "url": GITHUB_MCP_URL,
                "name": "github",
                "authorization_token": settings.github_token,
            }
        ],
        betas=["mcp-client-2025-04-04"],
    )

    # Extract JSON from response
    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    # Parse JSON
    try:
        clean = raw_text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        return json.loads(clean)
    except Exception as e:
        print(f"[MCP] Failed to parse response: {e}")
        # Fallback to original github_service
        from app.services.github_service import fetch_full_repo_data
        return await fetch_full_repo_data(f"https://github.com/{owner}/{repo}")


async def fetch_full_repo_data_mcp(url: str) -> dict:
    """
    Main entry point - replaces fetch_full_repo_data from github_service.py
    """
    owner, repo = parse_repo_url(url)

    try:
        data = await fetch_repo_data_via_mcp(owner, repo)
        # Ensure owner/repo keys exist
        data["owner"] = owner
        data["repo"] = repo
        return data
    except Exception as e:
        print(f"[MCP] Error, falling back to REST API: {e}")
        # Fallback to original github_service if MCP fails
        from app.services.github_service import fetch_full_repo_data
        return await fetch_full_repo_data(url)

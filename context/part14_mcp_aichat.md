# CONTEXT FILE: Part 14 - GitHub MCP Server + AI Chat Redirect + Scoring Fix
# Project: RepoInsight
# Three major additions in this part.

---

## What This Part Adds

1. GitHub MCP Server integration (replaces github_service.py raw REST calls)
2. AI Chat Redirect feature (ChatGPT, Gemini, Claude buttons on opportunity cards)
3. Opportunity scoring accuracy fix

---

## Feature 1: GitHub MCP Server Integration

### What is MCP
Model Context Protocol (MCP) is an open standard by Anthropic that lets LLMs
use external tools through a structured interface. Instead of writing custom
GitHub API wrapper code, we use GitHub's official MCP server which exposes
GitHub operations as LLM-callable tools.

### Why Replace github_service.py
- github_service.py makes raw httpx REST calls (custom code to maintain)
- GitHub MCP server is official, maintained, handles auth, pagination, errors
- LLMs can call GitHub tools directly in the analysis pipeline
- Resume value: "Integrated GitHub MCP Server for structured tool-use in LLM pipeline"

### Installation

Add to backend/requirements.txt:
```
mcp==1.0.0
anthropic[mcp]==0.40.0
```

### New File: backend/app/services/github_mcp_service.py

```python
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
```

### Update backend/app/tasks/analysis_task.py

Change the import at the top:

```python
# Replace this:
from app.services.github_service import fetch_full_repo_data, parse_repo_url

# With this:
from app.services.github_mcp_service import fetch_full_repo_data_mcp as fetch_full_repo_data
from app.services.github_mcp_service import parse_repo_url
```

Everything else in analysis_task.py stays the same.
The MCP service has the same interface as github_service.py.

### Update backend/.env.example

MCP uses the same GITHUB_TOKEN already in .env. No new keys needed.

Add this comment to .env.example:
```
# GitHub token is used for both GitHub REST API and GitHub MCP Server
GITHUB_TOKEN=your_github_personal_access_token_here
```

### Keep github_service.py

Do NOT delete github_service.py. It serves as the fallback when MCP fails.
The MCP service imports it as fallback automatically.

---

## Feature 2: AI Chat Redirect (ChatGPT / Gemini / Claude)

### How It Works

When user opens a contribution opportunity card and clicks an AI button:
1. System constructs a rich context prompt from repo + opportunity data
2. For ChatGPT: opens `https://chat.openai.com/?q=ENCODED_PROMPT`
3. For Gemini: opens `https://gemini.google.com/app?q=ENCODED_PROMPT`
4. For Claude: copies prompt to clipboard, opens `https://claude.ai`, shows toast
5. User continues the conversation with full project context pre-loaded

### New Backend Endpoint

### File: backend/app/routes/repos.py (ADD this endpoint)

```python
@router.get("/repos/{repo_id}/opportunities/{opportunity_id}/ai-context")
async def get_ai_context(
    repo_id: int,
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a context prompt for AI chat redirect.
    Returns the full context string that gets passed to ChatGPT/Gemini/Claude.
    """
    # Get repo
    repo_result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get current analysis
    analysis_result = await db.execute(
        select(RepositoryAnalysis).where(
            RepositoryAnalysis.repo_id == repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    analysis = analysis_result.scalar_one_or_none()

    # Get opportunity
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Build tech stack string
    tech_stack = analysis.tech_stack or {} if analysis else {}
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "not detected"
    language = repo.language or "Unknown"

    # Build architecture snippet (truncated)
    arch_snippet = ""
    if analysis and analysis.architecture_explanation:
        arch_snippet = analysis.architecture_explanation[:400].replace("\n", " ")

    # Build context prompt
    context_prompt = f"""PROJECT CONTEXT
===============
Repository: {repo.full_name}
Description: {repo.description or 'No description'}
Language: {language}
Frameworks: {frameworks}
GitHub: {repo.url}

Architecture Overview:
{arch_snippet}

CONTRIBUTION TASK
=================
Title: {opp.title}
Category: {opp.category or 'general'}
Difficulty: {opp.difficulty}/10
Estimated Time: {opp.estimated_hours}h
Impact: {opp.impact}/10
Learning Value: {opp.learning_value}/10

What Needs to Be Done:
{opp.description or 'See GitHub issue for details'}
{f'GitHub Issue: {opp.github_issue_url}' if opp.github_issue_url else ''}

MY REQUEST
==========
I want to implement this contribution to {repo.full_name}.
Please help me with:
1. What exactly needs to be changed in the codebase
2. Which files to open first and why
3. Step-by-step implementation plan
4. What edge cases to handle
5. How to write tests for this change
6. How to write a good Pull Request description

Start by summarizing what you understand about the task,
then ask me any clarifying questions."""

    return {
        "context_prompt": context_prompt,
        "repo_full_name": repo.full_name,
        "opportunity_title": opp.title,
        "char_count": len(context_prompt),
    }
```

### New Frontend Component

### File: frontend/src/components/Opportunities/AIHelperButtons.tsx (NEW)

```tsx
import { useState } from 'react';

interface Props {
  repoId: number;
  opportunityId: number;
  opportunityTitle: string;
}

export function AIHelperButtons({ repoId, opportunityId, opportunityTitle }: Props) {
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState('');

  const fetchContext = async (): Promise<string> => {
    const res = await fetch(`/api/repos/${repoId}/opportunities/${opportunityId}/ai-context`);
    const data = await res.json();
    return data.context_prompt;
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleChatGPT = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      const encoded = encodeURIComponent(prompt);
      // ChatGPT URL limit ~2000 chars - truncate if needed
      const safeEncoded = encoded.length > 2000
        ? encodeURIComponent(prompt.slice(0, 1400) + '\n\n[Context truncated - ask me for more details]')
        : encoded;
      window.open(`https://chat.openai.com/?q=${safeEncoded}`, '_blank');
      showToast('Opening ChatGPT with project context...');
    } catch (e) {
      showToast('Failed to load context. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGemini = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      const encoded = encodeURIComponent(prompt);
      const safeEncoded = encoded.length > 2000
        ? encodeURIComponent(prompt.slice(0, 1400) + '\n\n[Context truncated]')
        : encoded;
      window.open(`https://gemini.google.com/app?q=${safeEncoded}`, '_blank');
      showToast('Opening Gemini with project context...');
    } catch (e) {
      showToast('Failed to load context. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClaude = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      await navigator.clipboard.writeText(prompt);
      window.open('https://claude.ai', '_blank');
      showToast('Context copied! Paste it in Claude (Cmd+V / Ctrl+V)');
    } catch (e) {
      showToast('Failed to copy context. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const buttons = [
    {
      label: 'ChatGPT',
      icon: '🤖',
      color: '#10a37f',
      onClick: handleChatGPT,
    },
    {
      label: 'Gemini',
      icon: '✨',
      color: '#1a73e8',
      onClick: handleGemini,
    },
    {
      label: 'Claude',
      icon: '🔮',
      color: '#d97757',
      onClick: handleClaude,
      note: '(copies context)',
    },
  ];

  return (
    <div>
      <p
        className="text-xs font-medium mb-2"
        style={{ color: '#57606a' }}
      >
        Get AI help implementing this:
      </p>

      <div className="flex gap-2 flex-wrap">
        {buttons.map((btn) => (
          <button
            key={btn.label}
            onClick={btn.onClick}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium text-white transition-opacity"
            style={{
              backgroundColor: btn.color,
              opacity: loading ? 0.6 : 1,
            }}
          >
            <span>{btn.icon}</span>
            <span>Ask {btn.label}</span>
            {btn.note && (
              <span style={{ opacity: 0.8, fontSize: '10px' }}>{btn.note}</span>
            )}
          </button>
        ))}
      </div>

      {toast && (
        <div
          className="mt-2 text-xs px-3 py-2 rounded"
          style={{
            backgroundColor: '#dafbe1',
            color: '#2ea44f',
            border: '1px solid #9be9a8',
          }}
        >
          {toast}
        </div>
      )}

      <p
        className="text-xs mt-2"
        style={{ color: '#8b949e' }}
      >
        Full project context + this task is passed to the AI automatically.
      </p>
    </div>
  );
}
```

### Update frontend/src/components/Opportunities/OpportunityDetail.tsx

Add import at top:
```typescript
import { AIHelperButtons } from './AIHelperButtons';
```

Add AIHelperButtons section inside the modal body, after "How to Get Started":

```tsx
{/* AI Help Section */}
<div
  className="rounded-lg p-4"
  style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8' }}
>
  <AIHelperButtons
    repoId={repoId}
    opportunityId={opp.id}
    opportunityTitle={opp.title}
  />
</div>
```

Note: OpportunityDetail needs repoId passed as a prop.
Update the component signature:
```typescript
interface Props {
  opp: Opportunity;
  repoId: number;    // ADD THIS
  onClose: () => void;
}
```

Update OpportunityCard.tsx to pass repoId:
```tsx
{open && (
  <OpportunityDetail
    opp={opp}
    repoId={repoId}        // ADD THIS
    onClose={() => setOpen(false)}
  />
)}
```

OpportunityCard also needs repoId as prop:
```typescript
interface Props {
  opp: Opportunity;
  repoId: number;    // ADD THIS
}
```

Update OpportunityList.tsx to pass repoId down:
```typescript
interface Props {
  opportunities: Opportunity[];
  showFilter?: boolean;
  repoId: number;    // ADD THIS
}

// Inside map:
<OpportunityCard key={opp.id || i} opp={opp} repoId={repoId} />
```

Update ResultsDashboard.tsx to pass repoId to OpportunityList:
```tsx
<OpportunityList opportunities={opportunities} showFilter repoId={repoId} />
// and
<OpportunityList opportunities={matched} showFilter={false} repoId={repoId} />
```

---

## Feature 3: Fix Opportunity Scoring Accuracy

Current problem: ALL opportunities score 235 or 315 regardless of actual difficulty.
This is because impact/learning are hardcoded to 5 and 8 for all GitHub issues.

### Fix backend/app/services/scoring_engine.py

Replace score_github_issue function:

```python
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
```

---

## Validation Checklist

DATABASE (if not done):
[ ] ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS ai_suggestions JSONB;

MCP INTEGRATION:
[ ] mcp and anthropic[mcp] added to requirements.txt
[ ] backend/app/services/github_mcp_service.py created
[ ] analysis_task.py imports from github_mcp_service instead of github_service
[ ] github_service.py kept as fallback (do not delete)
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d
[ ] Test: analyze a repo, check worker logs for "[MCP]" messages
[ ] Fallback works: if MCP fails, analysis still completes via REST API

AI CHAT REDIRECT:
[ ] GET /api/repos/{repo_id}/opportunities/{opportunity_id}/ai-context added to repos.py
[ ] frontend/src/components/Opportunities/AIHelperButtons.tsx created
[ ] OpportunityDetail.tsx updated with repoId prop and AIHelperButtons
[ ] OpportunityCard.tsx updated with repoId prop
[ ] OpportunityList.tsx updated with repoId prop
[ ] ResultsDashboard.tsx passes repoId to OpportunityList
[ ] Test: open opportunity card, click "Ask ChatGPT"
[ ] Verify ChatGPT opens with project context pre-filled
[ ] Test: click "Ask Claude", verify context copied to clipboard
[ ] claude.ai opens in new tab
[ ] Toast notification appears with correct message

SCORING FIX:
[ ] score_github_issue replaced in scoring_engine.py
[ ] Re-analyze psf/requests
[ ] Verify: security/vulnerability issues score 9-10 impact
[ ] Verify: docs/typo issues score 3-4 impact
[ ] Verify: good first issue difficulty <= 3
[ ] Verify: scores are more varied (not all 235 or 315)

---

## Resume Update

Add to tech stack line:
"MCP Server (GitHub MCP)" 

Add to bullet points:
"Integrated GitHub MCP Server replacing custom REST layer with structured
LLM tool-use; built AI-assisted contribution workflow routing users to
ChatGPT, Gemini, or Claude with full project + task context pre-loaded,
enabling zero-cost AI guidance at scale."

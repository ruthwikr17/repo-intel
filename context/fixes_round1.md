# CONTEXT FILE: Fixes Round 1 - All Issues from Initial Review
# Project: RepoInsight
# Read the existing codebase before making any changes.
# Fix every issue listed. Do not add features not listed here.

---

## Summary of All Issues to Fix

1. Summary is one huge generic paragraph - needs restructuring
2. Summary is vague - prompt needs to extract real project details
3. Gemini API error - wrong model name
4. Setup guide shows raw markdown - needs proper rendering
5. Opportunities only shows AST fixes - missing features/docs suggestions
6. Opportunities filter defaults to user's selected tier - should show ALL
7. Matched page same filter issue
8. Time estimates are unrealistic (3-5 hours for simple fixes)
9. Home page skill/time selectors removed - bad UX
10. Not all 12 deliverables visible
11. Famous repos show no feature/doc contributions
12. UI dull, no dark mode
13. Nav buttons broken
14. Loading screen too basic
15. Only 3 PDFs instead of 4
16. Duplicate opportunities showing

---

## Fix 1 & 3: Gemini Model Name (CRITICAL - Fix First)

### File: backend/app/services/llm_service.py

Find this line:
```python
model_name="gemini-3.6-flash"
```

Replace with:
```python
model_name="gemini-3.6-flash"
```

Also update the call_gemini function to handle errors more gracefully:

```python
async def call_gemini(prompt: str, api_key: str) -> str:
    """Call Gemini API with given prompt and API key."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-3.6-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=3000,
            )
        )
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as e:
        # Log but don't crash - return empty string, Groq will fill in
        print(f"Gemini error: {str(e)}")
        return ""
```

And update the tier1 function to fallback to Groq when Gemini returns empty:

```python
async def run_tier1_analysis(repo_data: dict, gemini_key: str) -> dict:
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

    # Fallback: if Gemini failed, use Groq for those calls
    if not architecture:
        architecture = await call_groq(prompt_architecture(repo_data))
    if not walkthrough:
        walkthrough = await call_groq(prompt_code_walkthrough(repo_data))
    if not quality_report:
        quality_report = await call_groq(prompt_code_quality_report(repo_data))
    if not patterns_gotchas:
        patterns_gotchas = await call_groq(prompt_patterns_and_gotchas(repo_data))

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
```

---

## Fix 1 & 2: Summary Prompt Rewrite

### File: backend/app/services/prompts.py

Replace prompt_project_summary function entirely:

```python
def prompt_project_summary(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    languages = repo_data.get("languages", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    commits = repo_data.get("commits", [])[:5]
    contributors = repo_data.get("contributors", [])[:3]
    issues = repo_data.get("issues", [])[:5]

    lang_text = ", ".join(languages.keys()) if languages else "Unknown"
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "None detected"
    recent_commits = "\n".join(
        f"- {c.get('message', '')}" for c in commits
    ) or "No commits"
    top_contributors = ", ".join(
        c.get("login", "") for c in contributors
    ) or "Unknown"
    imports = ", ".join(ast.get("all_imports", [])[:10]) or "None"
    issue_titles = "\n".join(
        f"- {i.get('title', '')}" for i in issues
    ) or "No open issues"

    return f"""You are analyzing a real GitHub repository. Extract specific, factual details.

REPOSITORY DATA:
Name: {metadata.get('full_name', 'Unknown')}
Description: {metadata.get('description', 'No description provided')}
Language: {lang_text}
Frameworks detected: {frameworks}
Stars: {metadata.get('stars', 0)}
Forks: {metadata.get('forks', 0)}
Open issues: {metadata.get('open_issues_count', 0)}
License: {metadata.get('license', 'Unknown')}
Topics: {', '.join(metadata.get('topics', []))}
Key imports/dependencies found: {imports}
Files analyzed: {ast.get('files_analyzed', 0)}
Total functions: {ast.get('total_functions', 0)}
Has tests: {tech_stack.get('has_tests', False)}
Has CI/CD: {tech_stack.get('has_ci', False)}
Top contributors: {top_contributors}

Recent commits:
{recent_commits}

Open issues:
{issue_titles}

Write a structured project summary in EXACTLY this format. Be specific to THIS project, not generic:

**What It Does**
2-3 sentences explaining specifically what this project does, based on the name, description, imports, and code structure. Be concrete.

**How It Works**
2-3 sentences on the technical approach. Mention actual technologies, frameworks, and patterns detected.

**Who It's For**
1-2 sentences on target users or use cases.

**Project Health**
1-2 sentences on activity level, test coverage, and maintainability based on the data.

Do NOT write generic statements. Every sentence must be specific to THIS repository."""
```

---

## Fix 5, 11: Opportunities Prompt Rewrite

### File: backend/app/services/prompts.py

This prompt does not directly generate opportunities (scoring_engine.py does that from AST and GitHub issues). The real problem is the scoring engine only detects code smells. We need to ADD a new function that generates feature and documentation suggestions via LLM.

Add this new prompt function:

```python
def prompt_contribution_suggestions(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    issues = repo_data.get("issues", [])[:10]
    commits = repo_data.get("commits", [])[:10]

    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "None"
    has_tests = tech_stack.get("has_tests", False)
    has_ci = tech_stack.get("has_ci", False)
    has_docker = tech_stack.get("has_docker", False)
    files_analyzed = ast.get("files_analyzed", 0)
    total_functions = ast.get("total_functions", 0)
    imports = ", ".join(ast.get("all_imports", [])[:15])

    issue_text = "\n".join(
        f"- [{', '.join(i.get('labels', []))}] {i.get('title', '')}"
        for i in issues
    ) or "No open issues"

    return f"""You are an experienced open source maintainer reviewing this repository.
Suggest REALISTIC, SPECIFIC contribution opportunities beyond just code fixes.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', '')}
LANGUAGE: {metadata.get('language', 'Unknown')}
FRAMEWORKS: {frameworks}
KEY IMPORTS: {imports}
FILES: {files_analyzed}
FUNCTIONS: {total_functions}
HAS TESTS: {has_tests}
HAS CI: {has_ci}
HAS DOCKER: {has_docker}

EXISTING OPEN ISSUES:
{issue_text}

Based on this real repository data, suggest 8-12 contribution opportunities.
Include a MIX of types: features, documentation, testing, performance, tooling.

Return ONLY a valid JSON array. No explanation, no markdown, no backticks. Just the array.

Each item must have exactly these fields:
{{
  "title": "Short, specific title (max 80 chars)",
  "description": "2-3 sentences explaining what to do and why",
  "category": "feature|documentation|testing|performance|tooling|refactor",
  "difficulty": 1-10,
  "learning_value": 1-10,
  "impact": 1-10,
  "estimated_minutes": 30-180,
  "difficulty_tier": "beginner|intermediate|advanced",
  "github_issue_number": null,
  "github_issue_url": null
}}

Rules:
- estimated_minutes must be REALISTIC for someone using AI tools (30-180 minutes max)
- beginner = difficulty 1-3, intermediate = 4-6, advanced = 7-10
- At least 2 documentation suggestions
- At least 2 feature suggestions
- At least 1 testing suggestion
- If has_tests is false, strongly suggest adding tests
- If has_ci is false, suggest adding GitHub Actions
- If has_docker is false, suggest adding Dockerfile
- Be specific to THIS project's tech stack and purpose"""
```

### File: backend/app/services/llm_service.py

Add new import and function after existing functions:

```python
from app.services.prompts import prompt_contribution_suggestions
import json

async def generate_ai_opportunities(repo_data: dict, gemini_key: str = None) -> list:
    """
    Use LLM to generate feature/doc/testing contribution suggestions.
    Returns list of opportunity dicts.
    """
    prompt = prompt_contribution_suggestions(repo_data)
    
    # Try Gemini first, fallback to Groq
    raw = ""
    if gemini_key:
        raw = await call_gemini(prompt, gemini_key)
    
    if not raw:
        raw = await call_groq(prompt)
    
    # Parse JSON response
    try:
        # Strip any markdown if model added it
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        suggestions = json.loads(clean)
        if isinstance(suggestions, list):
            return suggestions[:12]
    except Exception as e:
        print(f"Failed to parse AI suggestions: {e}")
        return []
    
    return []
```

### File: backend/app/tasks/analysis_task.py

Update the task to call generate_ai_opportunities and merge with AST opportunities:

Add import at top:
```python
from app.services.llm_service import run_llm_analysis, generate_ai_opportunities
```

After Step 4 (LLM analysis), add Step 4.5:

```python
# Step 4.5: Generate AI contribution suggestions
self.update_state(state="PROGRESS", meta={"step": "Generating contribution ideas"})

ai_suggestions = asyncio.run(
    generate_ai_opportunities(
        combined_data,
        gemini_key=tier_info.get("gemini_key")
    )
)
```

In Step 5, update score_all_opportunities call:

```python
# Step 5: Score opportunities (AST issues + GitHub issues + AI suggestions)
github_issues = github_data.get("issues", [])
ast_issues = local_analysis.get("ast_analysis", {}).get("all_issues", [])
scored = score_all_opportunities(github_issues, ast_issues, ai_suggestions)
```

### File: backend/app/services/scoring_engine.py

Update score_all_opportunities function to accept ai_suggestions:

```python
def score_all_opportunities(
    github_issues: list[dict],
    ast_issues: list[dict],
    ai_suggestions: list[dict] = None,
    max_total: int = 30,
) -> dict:
    scored = []

    # Score GitHub issues
    for issue in github_issues:
        try:
            scored.append(score_github_issue(issue))
        except Exception:
            continue

    # Score AST code smells (cap at 10)
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
                
                scored.append({
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
                        suggestion.get("difficulty", 5)
                    ),
                    "estimated_hours": hours,
                    "difficulty_tier": suggestion.get("difficulty_tier", "intermediate"),
                })
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
```

---

## Fix 8: Time Estimates

### File: backend/app/services/scoring_engine.py

Replace estimate_hours function:

```python
def estimate_hours(difficulty: int, category: str) -> int:
    """
    Realistic estimates for developers using AI tools.
    In 2026, most tasks take 30 min - 2 hours with AI assistance.
    """
    base_hours = {
        1: 1,   # trivial: 1 hour
        2: 1,   # very easy: 1 hour
        3: 1,   # easy: 1 hour
        4: 2,   # moderate: 2 hours
        5: 2,   # medium: 2 hours
        6: 3,   # medium-hard: 3 hours
        7: 4,   # hard: 4 hours
        8: 6,   # very hard: 6 hours
        9: 8,   # expert: 8 hours
        10: 12  # extreme: 12 hours
    }
    hours = base_hours.get(difficulty, 2)
    if category == "documentation":
        hours = max(1, hours // 2)
    return hours
```

---

## Fix 6, 7: Opportunities Filter Shows ALL by Default

### File: frontend/src/components/Opportunities/OpportunityList.tsx

Change initial filter state from user's tier to 'all':

```tsx
const [filter, setFilter] = useState('all');
```

This should already be 'all' - verify it is not being overridden elsewhere.

Also in ResultsDashboard.tsx, the Opportunities tab should NOT pre-filter.
Remove any difficulty_tier parameter from the getOpportunities call:

```typescript
const [analysisData, oppsData] = await Promise.all([
  getAnalysis(repoId),
  getOpportunities(repoId),  // No tier filter - fetch ALL
]);
```

---

## Fix 9: Remove Skill/Time from Home Page

### File: frontend/src/components/Home/UrlInputForm.tsx

Replace entire file:

```tsx
import { useState } from 'react';
import type { AnalysisRequest } from '../../types';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';

interface Props {
  onSubmit: (data: AnalysisRequest) => void;
  loading: boolean;
  error: string | null;
}

export function UrlInputForm({ onSubmit, loading, error }: Props) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit({
      url: url.trim(),
      skill_level: 'intermediate',
      available_hours_per_week: 10,
      preferred_categories: [],
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="mb-10">
        <h1
          className="text-3xl font-bold mb-2"
          style={{ color: '#24292f', fontFamily: 'monospace' }}
        >
          Analyze any GitHub repository
        </h1>
        <p style={{ color: '#57606a' }}>
          Get AI-powered insights, architecture explanation,
          and contribution opportunities — instantly.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label
            className="block text-sm font-medium mb-1"
            style={{ color: '#24292f' }}
          >
            GitHub Repository URL
          </label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            className="w-full px-3 py-2 rounded border text-sm outline-none"
            style={{
              borderColor: '#d0d7de',
              fontFamily: 'monospace',
              color: '#24292f',
            }}
            disabled={loading}
          />
        </div>

        {error && <ErrorMessage message={error} />}

        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-white transition-opacity"
          style={{
            backgroundColor: '#2ea44f',
            opacity: loading || !url.trim() ? 0.6 : 1,
          }}
        >
          {loading ? <LoadingSpinner size="sm" /> : null}
          {loading ? 'Analyzing...' : 'Analyze Repository'}
        </button>
      </form>

      <div className="mt-8">
        <p className="text-xs mb-2" style={{ color: '#57606a' }}>
          Try with a popular repo:
        </p>
        <div className="flex flex-wrap gap-2">
          {[
            'https://github.com/psf/requests',
            'https://github.com/pallets/flask',
            'https://github.com/django/django',
            'https://github.com/encode/django-rest-framework',
          ].map((example) => (
            <button
              key={example}
              onClick={() => setUrl(example)}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: '#d0d7de',
                color: '#57606a',
                fontFamily: 'monospace',
              }}
              disabled={loading}
            >
              {example.replace('https://github.com/', '')}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Fix 4: Setup Guide Markdown Rendering

### Add react-markdown to frontend

```bash
cd frontend && npm install react-markdown
```

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

Add import at top:
```typescript
import ReactMarkdown from 'react-markdown';
```

Replace the Section component at bottom of file:

```tsx
function Section({
  title, content, code, markdown
}: {
  title: string;
  content: string;
  code?: boolean;
  markdown?: boolean;
}) {
  if (!content) return null;
  return (
    <div className="mb-8">
      <h2
        className="text-base font-semibold mb-3"
        style={{ color: '#24292f' }}
      >
        {title}
      </h2>
      {markdown ? (
        <div
          className="text-sm leading-relaxed rounded p-4 prose max-w-none"
          style={{
            backgroundColor: 'white',
            border: '1px solid #e1e4e8',
            color: '#24292f',
          }}
        >
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : (
        <div
          className="text-sm leading-relaxed rounded p-4"
          style={{
            backgroundColor: code ? '#f6f8fa' : 'white',
            color: '#24292f',
            border: '1px solid #e1e4e8',
            fontFamily: code ? 'monospace' : 'inherit',
            whiteSpace: code ? 'pre-wrap' : 'normal',
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
}
```

Update Setup Guide tab to use markdown:
```tsx
{tab === 'Setup Guide' && (
  <Section title="Setup Guide" content={analysis.setup_guide} markdown />
)}
```

Update Summary tab to use markdown:
```tsx
{tab === 'Summary' && (
  <Section title="Project Summary" content={analysis.summary} markdown />
)}
```

---

## Fix 12: Dark Mode Toggle

### File: frontend/src/App.tsx

Add dark mode state and toggle button:

```tsx
const [darkMode, setDarkMode] = useState(false);

// Apply dark mode to body
useEffect(() => {
  document.body.style.backgroundColor = darkMode ? '#0d1117' : '#f6f8fa';
  document.body.style.color = darkMode ? '#e6edf3' : '#24292f';
}, [darkMode]);
```

Add toggle button in Layout - pass darkMode and onToggleDark as props to Layout:

```tsx
<Layout
  currentView={view}
  onNavigate={...}
  repoName={repoName}
  darkMode={darkMode}
  onToggleDark={() => setDarkMode(!darkMode)}
>
```

### File: frontend/src/components/Layout/Sidebar.tsx

Add dark mode toggle at bottom of sidebar:

```tsx
interface SidebarProps {
  currentView: View;
  onNavigate: (view: View) => void;
  repoName?: string;
  darkMode?: boolean;
  onToggleDark?: () => void;
}

// Inside the component, add toggle button in footer area:
<div className="mt-auto flex flex-col gap-2">
  <button
    onClick={onToggleDark}
    className="text-xs px-3 py-2 rounded text-left flex items-center gap-2"
    style={{ color: '#8b949e' }}
  >
    {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
  </button>
  <p style={{ color: '#57606a', fontSize: '11px' }}>
    RepoInsight v1.0
  </p>
</div>
```

---

## Fix 13: Nav Buttons Broken

### File: frontend/src/components/Layout/Sidebar.tsx

The nav buttons use onNavigate but the view state in App.tsx may not be updating correctly.

In App.tsx, update the onNavigate handler:

```tsx
onNavigate={(v) => {
  if (v === 'home') {
    // Reset analysis state when going home
    setView('home');
  } else if (v === 'results' && repoId) {
    setView('results');
  } else if (v === 'repos') {
    setView('repos');
  }
}}
```

Also add the Recent Repos view in App.tsx JSX:

```tsx
{view === 'repos' && (
  <RecentReposView />
)}
```

### File: frontend/src/components/Home/RecentReposView.tsx (NEW)

```tsx
import { useState, useEffect } from 'react';
import { listRepos } from '../../api/client';

export function RecentReposView() {
  const [repos, setRepos] = useState<any[]>([]);

  useEffect(() => {
    listRepos().then((data) => setRepos(data.repositories));
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <h2
        className="text-xl font-bold mb-6"
        style={{ color: '#24292f', fontFamily: 'monospace' }}
      >
        Recently Analyzed
      </h2>
      {repos.length === 0 ? (
        <p style={{ color: '#57606a' }}>No repositories analyzed yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {repos.map((repo) => (
            <div
              key={repo.id}
              className="bg-white rounded border p-4"
              style={{ borderColor: '#e1e4e8' }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="font-medium text-sm"
                  style={{ color: '#24292f', fontFamily: 'monospace' }}
                >
                  {repo.full_name}
                </span>
                <span className="text-xs" style={{ color: '#57606a' }}>
                  ⭐ {repo.stars}
                </span>
              </div>
              {repo.description && (
                <p
                  className="text-xs mt-1"
                  style={{ color: '#57606a' }}
                >
                  {repo.description.slice(0, 100)}
                </p>
              )}
              <p className="text-xs mt-2" style={{ color: '#8b949e' }}>
                {repo.language} &bull; Analyzed{' '}
                {new Date(repo.last_analyzed_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Fix 14: Loading Screen Redesign

### File: frontend/src/components/Analysis/ProgressView.tsx

Replace entire file:

```tsx
import type { TaskStatus } from '../../types';

const STEPS = [
  { key: 'github', label: 'Fetching GitHub data', icon: '🐙' },
  { key: 'analyzing', label: 'Cloning & analyzing repository', icon: '🔬' },
  { key: 'tier', label: 'Selecting AI model tier', icon: '🤖' },
  { key: 'llm', label: 'Running AI analysis (8 parallel calls)', icon: '⚡' },
  { key: 'scoring', label: 'Scoring contribution opportunities', icon: '📊' },
  { key: 'saving', label: 'Saving results to database', icon: '💾' },
];

interface Props {
  taskStatus: TaskStatus | null;
}

export function ProgressView({ taskStatus }: Props) {
  const currentStep = taskStatus?.step?.toLowerCase() || '';

  const getStepState = (index: number) => {
    const stepKeywords = ['github', 'analyz', 'select', 'ai analysis', 'scor', 'sav'];
    const currentIndex = stepKeywords.findIndex((k) => currentStep.includes(k));

    if (currentIndex === -1) return 'waiting';
    if (index < currentIndex) return 'done';
    if (index === currentIndex) return 'active';
    return 'waiting';
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: '#f6f8fa' }}
    >
      <div className="w-full max-w-lg px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4"
            style={{ backgroundColor: '#dafbe1' }}>
            <span className="text-3xl">🔍</span>
          </div>
          <h2
            className="text-2xl font-bold"
            style={{ color: '#24292f', fontFamily: 'monospace' }}
          >
            Analyzing Repository
          </h2>
          <p className="mt-2 text-sm" style={{ color: '#57606a' }}>
            This takes 2-3 minutes. Grab a coffee ☕
          </p>
        </div>

        {/* Steps */}
        <div className="flex flex-col gap-0">
          {STEPS.map((step, i) => {
            const state = getStepState(i);
            return (
              <div key={step.key} className="flex items-start gap-4">
                {/* Connector + Icon */}
                <div className="flex flex-col items-center">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold flex-shrink-0 transition-all"
                    style={{
                      backgroundColor:
                        state === 'done' ? '#2ea44f' :
                        state === 'active' ? '#0969da' : '#e1e4e8',
                      color:
                        state === 'waiting' ? '#8b949e' : 'white',
                    }}
                  >
                    {state === 'done' ? '✓' : step.icon}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className="w-0.5 h-8"
                      style={{
                        backgroundColor: state === 'done' ? '#2ea44f' : '#e1e4e8'
                      }}
                    />
                  )}
                </div>

                {/* Label */}
                <div className="pt-2 pb-8">
                  <p
                    className="text-sm font-medium"
                    style={{
                      color:
                        state === 'done' ? '#2ea44f' :
                        state === 'active' ? '#0969da' : '#8b949e',
                    }}
                  >
                    {step.label}
                    {state === 'active' && (
                      <span className="ml-2 inline-flex gap-1">
                        <span className="animate-bounce" style={{animationDelay:'0ms'}}>.</span>
                        <span className="animate-bounce" style={{animationDelay:'150ms'}}>.</span>
                        <span className="animate-bounce" style={{animationDelay:'300ms'}}>.</span>
                      </span>
                    )}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

---

## Fix 15: Add 4th PDF Type (Code Quality)

The 4th PDF was already implemented in Part 12 as code_quality.
The issue is the frontend only shows 3 buttons.

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

Update the PDF download section to show all 4 types:

```tsx
{[
  { label: '📋 Contributor Guide', type: 'contributor_guide' },
  { label: '📊 Code Quality', type: 'code_quality' },
  { label: '📄 Executive Summary', type: 'executive_summary' },
  { label: '🔍 Full Analysis', type: 'contributor_guide' },
].map(({ label, type }) => (
  <button
    key={label}
    onClick={() => handleDownloadPdf(type)}
    disabled={downloading}
    className="text-xs px-3 py-1.5 rounded border transition-colors"
    style={{
      borderColor: '#d0d7de',
      color: '#57606a',
      backgroundColor: 'white',
      opacity: downloading ? 0.6 : 1,
    }}
  >
    {label}
  </button>
))}
```

---

## Validation Checklist

After all fixes, verify:

[ ] Architecture tab shows real content (not Gemini error)
[ ] Summary tab shows structured sections with **bold** headers
[ ] Setup guide renders markdown properly (not raw text)
[ ] Opportunities tab shows ALL by default (all tiers visible)
[ ] Opportunities include feature/doc/testing suggestions (not just fixes)
[ ] No duplicate opportunities shown
[ ] Matched tab shows all opportunities ranked
[ ] Time estimates max out at ~4 hours for most tasks
[ ] Home page has ONLY URL input (no skill/time selectors)
[ ] Nav buttons (Analyze Repo, Recent Repos) work correctly
[ ] Loading screen shows full-page vertical steps with icons
[ ] Dark mode toggle works in sidebar
[ ] 4 PDF download buttons visible in results
[ ] Rebuild: docker-compose down && docker-compose up --build -d
[ ] Re-analyze a repo with 50+ issues (use psf/requests) and verify results

---

## Notes for Windsurf

1. Fix the Gemini model name FIRST before anything else.
2. The AI suggestions feature (generate_ai_opportunities) adds a 9th LLM call.
   This is separate from the existing 8 calls and runs after them.
3. Deduplication in score_all_opportunities is critical - must dedupe by title.
4. react-markdown requires npm install before it can be used.
5. The RecentReposView is a new component that needs to be imported in App.tsx.
6. Dark mode is basic - just toggles sidebar state, not full CSS variables.
   A full dark mode overhaul can be a future improvement.

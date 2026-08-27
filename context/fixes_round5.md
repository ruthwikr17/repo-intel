# CONTEXT FILE: Fix Round 5 - Quality, Rendering, Expandable Cards
# Project: RepoInsight
# Three focused fixes: LLM prompt quality, markdown rendering, opportunity details

---

## Fix 1: Pass README Content to LLM Prompts (Summary Quality)

The current summary prompt only receives metadata (stars, forks, language).
The LLM guesses what the project does. We need to pass actual README content.

### Fix backend/app/services/github_service.py

Add a new function to fetch README content:

```python
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
```

Update fetch_full_repo_data to include readme:

```python
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
```

### Fix backend/app/services/prompts.py - prompt_project_summary

Replace the function with this version that uses README:

```python
def prompt_project_summary(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    languages = repo_data.get("languages", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")
    commits = repo_data.get("commits", [])[:5]
    contributors = repo_data.get("contributors", [])[:3]

    lang_text = ", ".join(languages.keys()) if languages else "Unknown"
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "None detected"
    imports = ", ".join(ast.get("all_imports", [])[:15]) or "None"
    recent_commits = "\n".join(
        f"- {c.get('message', '')}" for c in commits
    ) or "No commits"
    top_contributors = ", ".join(
        c.get("login", "") for c in contributors
    ) or "Unknown"

    readme_section = f"""
README CONTENT (first 3000 chars):
{readme}
""" if readme else "No README available."

    return f"""You are analyzing a real GitHub repository. Read ALL data carefully before writing.
Base your response ONLY on what is actually in this data. Do NOT invent or assume.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', 'No description')}
LANGUAGE: {lang_text}
FRAMEWORKS DETECTED: {frameworks}
KEY IMPORTS/LIBRARIES: {imports}
STARS: {metadata.get('stars', 0)}
FORKS: {metadata.get('forks', 0)}
OPEN ISSUES: {metadata.get('open_issues_count', 0)}
LICENSE: {metadata.get('license', 'Unknown')}
TOPICS: {', '.join(metadata.get('topics', []))}
TOP CONTRIBUTORS: {top_contributors}
HAS TESTS: {tech_stack.get('has_tests', False)}
HAS CI/CD: {tech_stack.get('has_ci', False)}
FILES ANALYZED: {ast.get('files_analyzed', 0)}
TOTAL FUNCTIONS: {ast.get('total_functions', 0)}

RECENT COMMITS:
{recent_commits}

{readme_section}

Based on ALL of the above, write a structured project summary using EXACTLY this markdown format:

## What It Does
2-3 sentences. Describe specifically what this project builds or enables.
Use concrete terms from the README, imports, and description. No vague statements.

## How It Works
2-3 sentences on the technical implementation. Name actual technologies, frameworks,
and patterns you can verify from the imports and code structure. Be specific.

## Who It's For
1-2 sentences on the intended users or use cases, based on README and project context.

## Project Health
1-2 sentences on activity level and maintainability based on the actual data provided.

RULES:
- Use ## headings exactly as shown
- Do NOT say "appears to" or "suggests" or "may" - only state what is clearly evident
- If README says X, say X. Quote the README when helpful.
- Keep each section under 4 sentences"""
```

Also update prompt_architecture to use readme:

```python
def prompt_architecture(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    structure = repo_data.get("directory_structure", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")

    imports = ast.get("all_imports", [])[:20]
    files_count = ast.get("files_analyzed", 0)
    avg_complexity = ast.get("avg_complexity", 0)
    total_functions = ast.get("total_functions", 0)
    total_classes = ast.get("total_classes", 0)

    structure_summary = []
    if isinstance(structure, dict) and "children" in structure:
        for child in structure.get("children", [])[:10]:
            name = child.get("name", "")
            type_ = child.get("type", "")
            if type_ == "dir":
                structure_summary.append(f"- {name}/")
            else:
                structure_summary.append(f"- {name}")

    readme_section = f"README EXCERPT:\n{readme[:2000]}" if readme else ""

    return f"""You are a senior software architect. Analyze this repository's architecture.
Base your response ONLY on the actual data provided.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
LANGUAGE: {metadata.get('language', 'Unknown')}
FRAMEWORKS: {', '.join(tech_stack.get('frameworks', []))}

TOP-LEVEL STRUCTURE:
{chr(10).join(structure_summary) or 'Not available'}

CODE METRICS:
- Files analyzed: {files_count}
- Total functions: {total_functions}
- Total classes: {total_classes}
- Average complexity: {avg_complexity}
- Key imports: {', '.join(imports[:15])}

HAS TESTS: {tech_stack.get('has_tests', False)}
HAS DOCKER: {tech_stack.get('has_docker', False)}
HAS CI: {tech_stack.get('has_ci', False)}

{readme_section}

Write a detailed architecture explanation in markdown using these EXACT headings:

## Module Structure
Describe what each top-level folder contains and its purpose.

## Key Components
Name the most important classes and functions and what they do.

## Data Flow
Describe how data moves through the system from input to output.

## Design Patterns
Name specific patterns used (REST, MVC, Pipeline, etc.) with evidence.

## Where to Start
Tell a new contributor which file to open first and why.

Use ## headings. Use bullet points inside sections. Be specific to THIS project."""
```

---

## Fix 2: Markdown Rendering for ALL Text Sections

### Fix frontend/src/components/Analysis/ResultsDashboard.tsx

First ensure react-markdown is installed:
In frontend/package.json dependencies, add:
```
"react-markdown": "^9.0.0"
```
Run: cd frontend && npm install react-markdown

Then update the import at the top of ResultsDashboard.tsx:
```typescript
import ReactMarkdown from 'react-markdown';
```

Replace the Section component entirely:

```tsx
function Section({
  title,
  content,
  code = false,
}: {
  title: string;
  content: string;
  code?: boolean;
}) {
  if (!content) return null;

  // Check if content contains Gemini error message
  const hasError = content.includes('[Gemini Error') || content.includes('Error:');

  return (
    <div className="mb-8">
      <h2
        className="text-base font-semibold mb-3"
        style={{ color: '#24292f' }}
      >
        {title}
      </h2>
      <div
        className="rounded border"
        style={{
          border: '1px solid #e1e4e8',
          backgroundColor: hasError ? '#fff8f0' : 'white',
        }}
      >
        {code ? (
          <div
            style={{
              backgroundColor: '#f6f8fa',
              padding: '16px',
              fontFamily: 'monospace',
              fontSize: '13px',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
              color: '#24292f',
            }}
          >
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <div
            style={{ padding: '16px' }}
            className="prose prose-sm max-w-none"
          >
            <ReactMarkdown
              components={{
                h1: ({node, ...props}) => (
                  <h1 style={{fontSize:'18px', fontWeight:'700', color:'#24292f', marginBottom:'8px', marginTop:'16px'}} {...props} />
                ),
                h2: ({node, ...props}) => (
                  <h2 style={{fontSize:'15px', fontWeight:'600', color:'#24292f', marginBottom:'6px', marginTop:'16px', paddingBottom:'4px', borderBottom:'1px solid #e1e4e8'}} {...props} />
                ),
                h3: ({node, ...props}) => (
                  <h3 style={{fontSize:'13px', fontWeight:'600', color:'#24292f', marginBottom:'4px', marginTop:'12px'}} {...props} />
                ),
                p: ({node, ...props}) => (
                  <p style={{fontSize:'13px', lineHeight:'1.7', color:'#24292f', marginBottom:'10px'}} {...props} />
                ),
                li: ({node, ...props}) => (
                  <li style={{fontSize:'13px', lineHeight:'1.7', color:'#24292f', marginBottom:'4px'}} {...props} />
                ),
                ul: ({node, ...props}) => (
                  <ul style={{paddingLeft:'20px', marginBottom:'10px'}} {...props} />
                ),
                ol: ({node, ...props}) => (
                  <ol style={{paddingLeft:'20px', marginBottom:'10px'}} {...props} />
                ),
                strong: ({node, ...props}) => (
                  <strong style={{fontWeight:'600', color:'#24292f'}} {...props} />
                ),
                code: ({node, ...props}) => (
                  <code style={{backgroundColor:'#f6f8fa', padding:'2px 6px', borderRadius:'4px', fontFamily:'monospace', fontSize:'12px'}} {...props} />
                ),
                pre: ({node, ...props}) => (
                  <pre style={{backgroundColor:'#f6f8fa', border:'1px solid #e1e4e8', borderRadius:'6px', padding:'12px', fontFamily:'monospace', fontSize:'12px', overflowX:'auto', marginBottom:'10px'}} {...props} />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
```

Update ALL tab content to use the Section component with markdown:

```tsx
{tab === 'Summary' && (
  <Section title="Project Summary" content={analysis.summary} />
)}

{tab === 'Architecture' && (
  <>
    <Section title="Architecture" content={analysis.architecture_explanation} />
    <Section title="Code Walkthrough" content={analysis.code_walkthrough} />
    <Section title="Common Patterns & Gotchas" content={analysis.common_patterns} />
  </>
)}

{tab === 'Setup Guide' && (
  <Section title="Setup Guide" content={analysis.setup_guide} code />
)}
```

---

## Fix 3: Expandable Opportunity Cards with Full Detail

### New file: frontend/src/components/Opportunities/OpportunityDetail.tsx

```tsx
import { DifficultyBadge } from './DifficultyBadge';
import type { Opportunity } from '../../types';

interface Props {
  opp: Opportunity;
  onClose: () => void;
}

export function OpportunityDetail({ opp, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-screen overflow-y-auto"
        style={{ border: '1px solid #e1e4e8' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between p-5"
          style={{ borderBottom: '1px solid #e1e4e8' }}
        >
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <DifficultyBadge tier={opp.difficulty_tier} />
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#f6f8fa', color: '#57606a' }}
              >
                {opp.category}
              </span>
            </div>
            <h2
              className="text-base font-semibold"
              style={{ color: '#24292f' }}
            >
              {opp.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-xl font-light"
            style={{ color: '#57606a' }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-5">

          {/* Match score if available */}
          {opp.match_percentage !== undefined && (
            <div
              className="rounded p-3 flex items-center gap-3"
              style={{
                backgroundColor: opp.recommended ? '#dafbe1' : '#fff3e0',
                border: `1px solid ${opp.recommended ? '#9be9a8' : '#ffcc80'}`
              }}
            >
              <span style={{ fontSize: '20px' }}>
                {opp.recommended ? '✅' : '⚠️'}
              </span>
              <div>
                <p
                  className="text-sm font-medium"
                  style={{ color: opp.recommended ? '#2ea44f' : '#fb8500' }}
                >
                  {opp.match_percentage}% match for your profile
                </p>
                <p className="text-xs" style={{ color: '#57606a' }}>
                  {opp.recommended
                    ? 'This is a good fit for your skill level and availability.'
                    : 'This may be outside your current skill level or time constraints.'}
                </p>
              </div>
            </div>
          )}

          {/* What to do */}
          <div>
            <h3
              className="text-sm font-semibold mb-2"
              style={{ color: '#24292f' }}
            >
              What to Do
            </h3>
            <p className="text-sm" style={{ color: '#24292f', lineHeight: '1.7' }}>
              {opp.description || 'No description available.'}
            </p>
          </div>

          {/* Metrics */}
          <div>
            <h3
              className="text-sm font-semibold mb-3"
              style={{ color: '#24292f' }}
            >
              Task Metrics
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Difficulty', value: `${opp.difficulty}/10` },
                { label: 'Learning Value', value: `${opp.learning_value}/10` },
                { label: 'Impact', value: `${opp.impact}/10` },
                { label: 'Estimated Time', value: `${opp.estimated_hours}h` },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="rounded p-3 text-center"
                  style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8' }}
                >
                  <p
                    className="text-lg font-bold"
                    style={{ color: '#24292f' }}
                  >
                    {value}
                  </p>
                  <p className="text-xs" style={{ color: '#57606a' }}>
                    {label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Why it matters */}
          <div>
            <h3
              className="text-sm font-semibold mb-2"
              style={{ color: '#24292f' }}
            >
              Why It Matters
            </h3>
            <p className="text-sm" style={{ color: '#57606a', lineHeight: '1.7' }}>
              {opp.category === 'documentation' &&
                'Good documentation helps new contributors onboard faster and reduces repeated questions to maintainers.'}
              {opp.category === 'feature' &&
                'This feature has been requested by users and would improve the project\'s functionality and adoption.'}
              {opp.category === 'refactor' &&
                'Refactoring improves code readability and maintainability, making future contributions easier.'}
              {opp.category === 'testing' &&
                'Adding tests prevents regressions and gives contributors confidence when making changes.'}
              {opp.category === 'performance' &&
                'Performance improvements directly impact user experience and system reliability.'}
              {opp.category === 'tooling' &&
                'Tooling improvements (CI, linting, Docker) reduce friction for all contributors.'}
              {!['documentation','feature','refactor','testing','performance','tooling'].includes(opp.category || '') &&
                'Completing this contribution improves the overall quality and health of the project.'}
            </p>
          </div>

          {/* How to get started */}
          <div>
            <h3
              className="text-sm font-semibold mb-2"
              style={{ color: '#24292f' }}
            >
              How to Get Started
            </h3>
            <div className="flex flex-col gap-2">
              {[
                '1. Fork the repository and clone your fork locally',
                '2. Create a new branch: git checkout -b your-branch-name',
                '3. Make your changes following the project\'s code style',
                '4. Run the test suite to ensure nothing is broken',
                '5. Commit with a clear message and open a Pull Request',
              ].map((step) => (
                <p
                  key={step}
                  className="text-sm"
                  style={{ color: '#24292f', lineHeight: '1.6' }}
                >
                  {step}
                </p>
              ))}
            </div>
          </div>

          {/* GitHub Issue Link */}
          {opp.github_issue_url && (
            <div>
              <h3
                className="text-sm font-semibold mb-2"
                style={{ color: '#24292f' }}
              >
                GitHub Issue
              </h3>
              <a
                href={opp.github_issue_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm underline"
                style={{ color: '#0969da' }}
              >
                #{opp.github_issue_number} — View on GitHub →
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex justify-end p-4 gap-2"
          style={{ borderTop: '1px solid #e1e4e8' }}
        >
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded border"
            style={{ borderColor: '#d0d7de', color: '#57606a' }}
          >
            Close
          </button>
          {opp.github_issue_url && (
            <a
              href={opp.github_issue_url}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 text-sm rounded text-white"
              style={{ backgroundColor: '#2ea44f' }}
            >
              View Issue on GitHub
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Update frontend/src/components/Opportunities/OpportunityCard.tsx

Make the card clickable and open the detail modal:

```tsx
import { useState } from 'react';
import { DifficultyBadge } from './DifficultyBadge';
import { OpportunityDetail } from './OpportunityDetail';
import type { Opportunity } from '../../types';

export function OpportunityCard({ opp }: { opp: Opportunity }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div
        className="bg-white rounded border p-4 cursor-pointer transition-all"
        style={{ borderColor: '#e1e4e8' }}
        onClick={() => setOpen(true)}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#2ea44f';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#e1e4e8';
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <p className="text-sm font-medium" style={{ color: '#24292f' }}>
            {opp.title}
          </p>
          <DifficultyBadge tier={opp.difficulty_tier} />
        </div>

        {/* Description preview */}
        {opp.description && (
          <p className="text-xs mb-3" style={{ color: '#57606a' }}>
            {opp.description.slice(0, 120)}
            {opp.description.length > 120 ? '...' : ''}
          </p>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: '#57606a' }}>
          <span>⏱ {opp.estimated_hours}h</span>
          <span>📚 Learning: {opp.learning_value}/10</span>
          <span>💥 Impact: {opp.impact}/10</span>
          {opp.match_percentage !== undefined && (
            <span
              className="font-medium"
              style={{ color: opp.recommended ? '#2ea44f' : '#e03e2d' }}
            >
              {opp.match_percentage}% match
            </span>
          )}
          {opp.github_issue_url && (
            <span style={{ color: '#0969da' }}>
              #{opp.github_issue_number}
            </span>
          )}
        </div>

        {/* Click hint */}
        <p
          className="text-xs mt-2"
          style={{ color: '#8b949e' }}
        >
          Click to view details →
        </p>
      </div>

      {open && (
        <OpportunityDetail opp={opp} onClose={() => setOpen(false)} />
      )}
    </>
  );
}
```

---

## Validation Checklist

[ ] get_repo_readme() function added to github_service.py
[ ] fetch_full_repo_data includes readme in asyncio.gather and return dict
[ ] prompt_project_summary uses readme content
[ ] prompt_architecture uses readme content
[ ] react-markdown installed (npm install react-markdown in frontend/)
[ ] Section component in ResultsDashboard replaced with markdown-rendering version
[ ] All tabs use Section component (Summary, Architecture, Setup Guide)
[ ] OpportunityDetail.tsx created as new file
[ ] OpportunityCard.tsx updated to be clickable + open modal
[ ] OpportunityDetail imported in OpportunityCard
[ ] Rebuild backend: docker-compose down && docker-compose up --build -d
[ ] Rebuild frontend: npm run build (or restart dev server)
[ ] Re-analyze a repo (fresh analysis to get README-enriched data)
[ ] Summary shows structured sections with ## headings
[ ] Architecture tab shows properly formatted markdown
[ ] Setup guide renders with code blocks and bullet points
[ ] Clicking any opportunity card opens the detail modal
[ ] Detail modal shows metrics, what to do, how to start, GitHub link
[ ] Modal closes on ✕ button or clicking overlay

---

## Note for Windsurf

The most important change is get_repo_readme() in github_service.py.
Without README content in the prompt, the LLM will always give generic summaries.
This single change will dramatically improve summary and architecture quality.

After rebuilding, test with a repo that has a good README (psf/requests, pallets/flask)
to verify the summary now reflects actual project content.

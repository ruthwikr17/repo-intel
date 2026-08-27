# CONTEXT FILE: Fix Round 8 - Critical Fixes
# ALL issues must be fixed. Read every section carefully.

---

## ISSUE 1: Common Patterns / Gotchas Duplication (FINAL FIX)

ROOT CAUSE:
The LLM prompt for patterns_and_gotchas returns ONE response containing BOTH sections.
This gets stored in analysis.common_patterns field.
The frontend shows it TWICE - once under "Common Patterns" tab and once under "Gotchas & Tips" tab.
Both tabs show the same content because both read from analysis.common_patterns.

FIX - Backend: Split into two separate fields and two separate LLM calls.

### File: backend/app/models/analysis.py

The field gotchas_and_tips already exists but is currently set equal to common_patterns in tasks.
Verify this line in analysis_task.py:
```python
gotchas_and_tips=llm_results.get("common_patterns"),  # WRONG - same as common_patterns
```

### File: backend/app/services/prompts.py

REPLACE prompt_patterns_and_gotchas with TWO separate functions:

```python
def prompt_common_patterns(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    tech_stack = repo_data.get("tech_stack", {})
    file_results = ast.get("file_results", {})
    all_imports = ast.get("all_imports", [])[:20]
    frameworks = tech_stack.get("frameworks", [])

    file_patterns = []
    for filepath, data in list(file_results.items())[:10]:
        for func in data.get("functions", [])[:2]:
            file_patterns.append(f"{filepath}:{func['name']}")

    return f"""You are describing the coding conventions of this specific project.
RULES:
- Describe ONLY patterns visible in the actual code data below
- Each pattern must reference a real file, function, or import from the data
- Do NOT repeat anything that would belong in "gotchas" or "warnings"
- No generic advice. Only project-specific observations.
- Use ## Common Patterns as the only heading

REPOSITORY: {metadata.get('full_name', 'Unknown')}
FRAMEWORKS: {', '.join(frameworks)}
KEY IMPORTS: {', '.join(all_imports)}
SAMPLE FILE:FUNCTION PAIRS: {', '.join(file_patterns[:15])}

Write ONLY a ## Common Patterns section with 4-5 bullet points.
Each bullet: **Pattern Name**: One sentence describing it with a real example.
No other headings. No gotchas. No warnings."""


def prompt_gotchas_and_tips(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    tech_stack = repo_data.get("tech_stack", {})
    all_issues = ast.get("all_issues", [])[:10]
    readme = repo_data.get("readme", "")

    issues_text = "\n".join(
        f"- [{i['file']}] {i['issue']}" for i in all_issues
    ) or "No issues detected"

    return f"""You are warning a new contributor about pitfalls in this project.
RULES:
- Write ONLY warnings, pitfalls, and non-obvious requirements
- Base warnings on the actual detected issues and project structure
- Do NOT describe patterns or conventions (those are in a separate section)
- No generic advice like "write tests" unless tests are actually missing here
- Use ## Gotchas & Tips as the only heading

REPOSITORY: {metadata.get('full_name', 'Unknown')}
HAS TESTS: {tech_stack.get('has_tests', False)}
HAS CI: {tech_stack.get('has_ci', False)}
DETECTED CODE ISSUES:
{issues_text}

README EXCERPT:
{readme[:800] if readme else 'No README'}

Write ONLY a ## Gotchas & Tips section with 4-5 bullet points.
Each bullet: **Warning Title**: What will go wrong and how to avoid it.
No other headings. No patterns. No conventions."""
```

### File: backend/app/services/llm_service.py

Update run_tier1_analysis and run_tier2_analysis to make SEPARATE calls:

```python
# In both run_tier1_analysis and run_tier2_analysis,
# replace the single patterns call with two calls:

# REMOVE this:
# call_gemini(prompt_patterns_and_gotchas(repo_data), gemini_key),

# ADD these two separate calls:
# call_gemini(prompt_common_patterns(repo_data), gemini_key),
# call_gemini(prompt_gotchas_and_tips(repo_data), gemini_key),
```

Updated run_tier1_analysis:
```python
async def run_tier1_analysis(repo_data: dict, gemini_key: str) -> dict:
    from app.services.prompts import (
        prompt_project_summary, prompt_architecture,
        prompt_code_walkthrough, prompt_code_quality_report,
        prompt_setup_guide, prompt_contributor_guide_narrative,
        prompt_executive_summary, prompt_common_patterns,
        prompt_gotchas_and_tips
    )

    (
        summary,
        architecture,
        walkthrough,
        quality_report,
        setup_guide,
        contributor_narrative,
        executive_summary,
        common_patterns,
        gotchas,
    ) = await asyncio.gather(
        call_groq(prompt_project_summary(repo_data)),
        call_gemini(prompt_architecture(repo_data), gemini_key),
        call_gemini(prompt_code_walkthrough(repo_data), gemini_key),
        call_gemini(prompt_code_quality_report(repo_data), gemini_key),
        call_groq(prompt_setup_guide(repo_data)),
        call_groq(prompt_contributor_guide_narrative(repo_data)),
        call_groq(prompt_executive_summary(repo_data)),
        call_gemini(prompt_common_patterns(repo_data), gemini_key),
        call_groq(prompt_gotchas_and_tips(repo_data)),
    )

    # Fallbacks
    if not architecture:
        architecture = await call_groq(prompt_architecture(repo_data))
    if not walkthrough:
        walkthrough = await call_groq(prompt_code_walkthrough(repo_data))
    if not quality_report:
        quality_report = await call_groq(prompt_code_quality_report(repo_data))
    if not common_patterns:
        common_patterns = await call_groq(prompt_common_patterns(repo_data))

    return {
        "quality_tier": "HIGH",
        "apis_used": ["gemini-3.6-flash", "groq-gpt-oss-120b"],
        "summary": summary,
        "architecture_explanation": architecture,
        "code_walkthrough": walkthrough,
        "code_quality_report": quality_report,
        "setup_guide": setup_guide,
        "contributor_guide_narrative": contributor_narrative,
        "executive_summary": executive_summary,
        "common_patterns": common_patterns,
        "gotchas_and_tips": gotchas,  # NOW SEPARATE
    }
```

Do the same for run_tier2_analysis (all Groq, same structure, 9 calls total).

### File: backend/app/tasks/analysis_task.py

Update the analysis save to use separate fields:
```python
analysis = RepositoryAnalysis(
    repo_id=repo.id,
    # ... existing fields ...
    common_patterns=llm_results.get("common_patterns"),
    gotchas_and_tips=llm_results.get("gotchas_and_tips"),  # NOW DIFFERENT
    # ... rest of fields ...
)
```

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

In Architecture tab, show them separately:
```tsx
{tab === 'Architecture' && (
  <>
    <Section title="Architecture" content={analysis.architecture_explanation} />
    <Section title="Code Walkthrough" content={analysis.code_walkthrough} />
    <Section title="Common Patterns" content={analysis.common_patterns} />
    <Section title="Gotchas & Tips" content={analysis.gotchas_and_tips} />
  </>
)}
```

Each section shows ONLY its own content. No duplication possible.

---

## ISSUE 2: Setup Guide - Format and Content Fix

### File: backend/app/services/prompts.py

Replace prompt_setup_guide entirely:

```python
def prompt_setup_guide(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    languages = repo_data.get("languages", {})
    readme = repo_data.get("readme", "")
    ast = repo_data.get("ast_analysis", {})

    manifests = tech_stack.get("manifests_found", [])
    has_docker = tech_stack.get("has_docker", False)
    has_tests = tech_stack.get("has_tests", False)
    lang = metadata.get("language", "Unknown")
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "none"
    all_imports = ast.get("all_imports", [])[:10]

    return f"""Write a concise, well-formatted setup guide for contributors.
RULES:
- Only include steps that are NECESSARY for this specific project
- Use exact terminal commands (not placeholders like <your-token>)
- Keep each section SHORT - 3-5 lines maximum
- Do NOT add unnecessary warnings, disclaimers, or generic advice
- Do NOT repeat information between sections

PROJECT DATA:
Repository: {metadata.get('full_name', 'Unknown')}
Language: {lang}
Frameworks: {frameworks}
Manifest files: {', '.join(manifests)}
Has Docker: {has_docker}
Has Tests: {has_tests}
Key libraries: {', '.join(all_imports)}

README (check for actual setup commands):
{readme[:2000] if readme else 'No README'}

Write EXACTLY this structure, nothing more:

## Prerequisites
[2-4 bullet points of required tools with versions if known]

## Setup
```bash
git clone https://github.com/{metadata.get('full_name', 'owner/repo')}.git
cd {metadata.get('name', 'repo')}
[dependency install command based on manifests]
[any env setup if mentioned in README]
```

## Run
```bash
[exact command to start the project]
```

## Test
```bash
[exact test command if has_tests is true, otherwise skip this section]
```

Keep total length under 300 words. Be direct and specific."""
```

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

Setup Guide tab should render with proper markdown AND code blocks.
Ensure the Section component handles triple-backtick code blocks:

```tsx
{tab === 'Setup Guide' && (
  <Section title="Setup Guide" content={analysis.setup_guide} markdown />
)}
```

The Section component with markdown=true and react-markdown will handle
code blocks automatically as <pre><code> elements.
Verify react-markdown is installed and the Section component uses it.

---

## ISSUE 3: Opportunities Only Shows "Fix" - LLM Prompt Fix

### File: backend/app/services/prompts.py

Replace prompt_contribution_suggestions entirely:

```python
def prompt_contribution_suggestions(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")
    issues = repo_data.get("issues", [])[:10]
    file_results = ast.get("file_results", {})

    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "none"
    has_tests = tech_stack.get("has_tests", False)
    has_ci = tech_stack.get("has_ci", False)
    has_docker = tech_stack.get("has_docker", False)
    lang = metadata.get("language", "Unknown")
    all_imports = ast.get("all_imports", [])[:20]
    key_files = list(file_results.keys())[:10]

    github_issues_text = "\n".join(
        f"- #{i.get('number')}: {i.get('title','')}"
        for i in issues
    ) or "No open issues"

    return f"""You are a senior open source contributor suggesting MEANINGFUL contributions.
STRICT RULES:
- Generate EXACTLY 10 suggestions
- MAXIMUM 2 suggestions can be refactoring or code fixes
- At least 3 must be NEW FEATURES or ENHANCEMENTS
- At least 2 must be DOCUMENTATION improvements
- At least 1 must be a TESTING improvement
- At least 1 must be TOOLING (CI/CD, Docker, linting, etc.)
- Think creatively about what this project is MISSING
- Each what_to_do must be 3-4 sentences with SPECIFIC implementation details
- Return ONLY valid JSON array, no other text

PROJECT:
Repository: {metadata.get('full_name', 'Unknown')}
Description: {metadata.get('description', '')}
Language: {lang}
Frameworks: {frameworks}
Key libraries: {', '.join(all_imports)}
Key files: {', '.join(key_files)}
Has tests: {has_tests}
Has CI: {has_ci}
Has Docker: {has_docker}

Open GitHub issues:
{github_issues_text}

README excerpt:
{readme[:1500] if readme else 'No README'}

Generate 10 diverse contribution ideas. Think: what would make this project
more useful, more complete, better documented, easier to use?

Return JSON array:
[
  {{
    "title": "Specific actionable title (max 70 chars)",
    "what_to_do": "3-4 sentences. Name specific files to edit, functions to add, exact implementation approach. What does the end result look like?",
    "why_it_matters": "1-2 sentences on concrete benefit.",
    "files_to_look_at": ["actual", "file", "names", "from", "key_files"],
    "category": "feature|documentation|testing|performance|tooling|refactor",
    "difficulty": 4,
    "learning_value": 7,
    "impact": 8,
    "estimated_minutes": 60,
    "difficulty_tier": "beginner|intermediate|advanced"
  }}
]

IMPORTANT: estimated_minutes range is 30-120. Never exceed 120."""
```

---

## ISSUE 4: Remove "Matched" Tab Entirely

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

Remove 'Matched' from TABS array:
```typescript
const TABS = ['Summary', 'Architecture', 'Setup Guide', 'Opportunities'];
// Removed 'Matched'
```

Remove all Matched tab JSX and related state:
- Remove userProfileSet state
- Remove localProfile state
- Remove matched state
- Remove getMatchedOpportunities call from useEffect
- Remove {tab === 'Matched' && ...} block

Simplify useEffect:
```typescript
useEffect(() => {
  const load = async () => {
    try {
      const [analysisData, oppsData] = await Promise.all([
        getAnalysis(repoId),
        getOpportunities(repoId),
      ]);
      setAnalysis(analysisData);
      setOpportunities(oppsData.opportunities);
    } catch (e: any) {
      setError('Failed to load analysis results');
    } finally {
      setLoading(false);
    }
  };
  load();
}, [repoId]);
```

---

## ISSUE 5: Gemini Chat Redirect - No Prompt Passed

The problem: Gemini's `?q=` parameter does not work reliably in 2026.
Gemini now uses a different URL scheme.

Fix: Use clipboard copy for Gemini too (same as Claude approach).

### File: frontend/src/components/Opportunities/AIHelperButtons.tsx

Replace handleGemini:
```typescript
const handleGemini = async () => {
  setLoading(true);
  try {
    const prompt = await fetchContext();
    await navigator.clipboard.writeText(prompt);
    window.open('https://gemini.google.com/app', '_blank');
    showToast('✅ Context copied! Paste in Gemini (Cmd+V / Ctrl+V)');
  } catch (e) {
    showToast('Failed. Try again.');
  } finally {
    setLoading(false);
  }
};
```

Also improve Claude toast to be more obvious:
```typescript
const handleClaude = async () => {
  setLoading(true);
  try {
    const prompt = await fetchContext();
    await navigator.clipboard.writeText(prompt);
    window.open('https://claude.ai', '_blank');
    showToast('✅ Context copied to clipboard! Paste it in Claude (Cmd+V / Ctrl+V)');
  } catch (e) {
    showToast('Failed. Try again.');
  } finally {
    setLoading(false);
  }
};
```

Update button labels to reflect clipboard behavior:
```tsx
const buttons = [
  {
    label: 'ChatGPT',
    icon: '🤖',
    color: '#10a37f',
    onClick: handleChatGPT,
    note: '(opens with context)',
  },
  {
    label: 'Gemini',
    icon: '✨',
    color: '#1a73e8',
    onClick: handleGemini,
    note: '(copies + opens)',
  },
  {
    label: 'Claude',
    icon: '🔮',
    color: '#d97757',
    onClick: handleClaude,
    note: '(copies + opens)',
  },
];
```

---

## ISSUE 6: PDF Formatting Fix (All Three PDFs)

The core problem: LLM returns markdown (##, **, `) but HTML templates
render it as raw text. The Jinja templates need to strip/convert markdown.

Add a Jinja2 custom filter to pdf_service.py:

### File: backend/app/services/pdf_service.py

```python
import re

def markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML for PDF rendering."""
    if not text:
        return ''
    
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # Code blocks
        if stripped.startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre>')
                in_code_block = True
            continue
        
        if in_code_block:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue
        
        # Headings
        if stripped.startswith('## '):
            html_lines.append(f'<h3>{stripped[3:]}</h3>')
        elif stripped.startswith('# '):
            html_lines.append(f'<h2>{stripped[2:]}</h2>')
        # Bullet points
        elif stripped.startswith('- ') or stripped.startswith('* '):
            content = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')
        # Bold inline
        elif stripped:
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
            content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
            html_lines.append(f'<p>{content}</p>')
        else:
            html_lines.append('<br>')
    
    return '\n'.join(html_lines)


def get_jinja_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters['md'] = markdown_to_html  # Register filter
    return env
```

Now update ALL three HTML templates to use the |md filter.

### backend/app/templates/contributor_guide.html

Replace all raw text rendering sections with |md filter:

In the summary section, replace:
```html
{% for line in analysis.summary.split('\n') %}...{% endfor %}
```
With:
```html
{{ analysis.summary | md | safe }}
```

Do the same for ALL text sections:
- `{{ analysis.summary | md | safe }}`
- `{{ analysis.architecture_explanation | md | safe }}`
- `{{ analysis.setup_guide | md | safe }}`
- `{{ analysis.gotchas_and_tips | md | safe }}`

Also add these CSS rules to the contributor_guide.html `<style>` block:
```css
li {
  margin-bottom: 6px;
  line-height: 1.6;
  color: #24292f;
  list-style-type: disc;
  margin-left: 16px;
}
h3 {
  font-size: 13px;
  font-weight: 600;
  color: #24292f;
  margin: 16px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e8e8e8;
}
```

### backend/app/templates/executive_summary.html

Replace summary rendering with:
```html
{{ analysis.summary | md | safe }}
```

### backend/app/templates/code_quality.html

Replace all text section rendering with |md filter:
```html
{{ analysis.architecture_explanation | md | safe }}
{{ analysis.common_patterns | md | safe }}
```

---

## ISSUE 7: "Full Analysis" PDF Not Downloading

The frontend has a button labeled "Full Analysis" that maps to "contributor_guide"
report type (duplicate). The actual fourth PDF type should be "comparison" but
that requires 2+ repos which complicates things.

Replace "Full Analysis" with "Comparison" and properly implement it,
OR change it to "Code Quality" (which already works).

Simplest fix: Remove the duplicate "Full Analysis" button, keep 3 buttons
that actually work. The comparison PDF needs multiple repos — defer to later.

### File: frontend/src/components/Analysis/ResultsDashboard.tsx

Update PDF buttons:
```tsx
{[
  { label: '📋 Contributor Guide', type: 'contributor_guide' },
  { label: '📊 Code Quality', type: 'code_quality' },
  { label: '📄 Executive Summary', type: 'executive_summary' },
].map(({ label, type }) => (
  <button
    key={type}
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
    {downloading ? '⏳ Generating...' : label}
  </button>
))}
```

---

## ISSUE 8: Remove API Quota from Analytics Dashboard

### File: frontend/src/components/Dashboard/AnalyticsDashboard.tsx

Remove the entire "API Quota Usage Today" section block:
```tsx
{/* DELETE THIS ENTIRE BLOCK */}
<div className="bg-white rounded-lg border p-5 mb-6"
  style={{ borderColor: '#e1e4e8' }}>
  <h3>API Quota Usage Today</h3>
  ...
</div>
```

Remove quota-related variables:
```typescript
// DELETE these:
const geminiAUsed = ...
const geminiALimit = ...
const geminiAPct = ...
// etc.
```

---

## ISSUE 9: Dark Mode - Full Fix

The current dark mode only changes the body background. Cards stay white.
Fix: Use CSS variables that change on a `dark` class added to `<html>`.

### File: frontend/src/index.css

Add CSS variables:
```css
:root {
  --bg-primary: #f6f8fa;
  --bg-card: #ffffff;
  --bg-code: #f6f8fa;
  --bg-sidebar: #0d1117;
  --text-primary: #24292f;
  --text-muted: #57606a;
  --text-faint: #8b949e;
  --border: #e1e4e8;
  --accent: #2ea44f;
}

html.dark {
  --bg-primary: #0d1117;
  --bg-card: #161b22;
  --bg-code: #21262d;
  --bg-sidebar: #010409;
  --text-primary: #e6edf3;
  --text-muted: #8b949e;
  --text-faint: #656d76;
  --border: #30363d;
  --accent: #3fb950;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}
```

### File: frontend/src/App.tsx

Toggle dark class on html element:
```typescript
const [darkMode, setDarkMode] = useState(false);

useEffect(() => {
  if (darkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}, [darkMode]);
```

### Update ALL components to use CSS variables

Replace hardcoded color values with CSS variables in every component.

Key replacements across all components:
```
'#24292f'  → 'var(--text-primary)'
'#57606a'  → 'var(--text-muted)'
'#8b949e'  → 'var(--text-faint)'
'#ffffff'  → 'var(--bg-card)'
'#f6f8fa'  → 'var(--bg-code)'
'#e1e4e8'  → 'var(--border)'
'#0d1117'  (sidebar bg) → 'var(--bg-sidebar)'
```

Files to update:
- ResultsDashboard.tsx
- OpportunityCard.tsx
- OpportunityDetail.tsx
- OpportunityList.tsx
- ProgressView.tsx
- UrlInputForm.tsx
- Sidebar.tsx
- Layout.tsx
- StatCard.tsx
- ActivityFeed.tsx
- SimpleBarChart.tsx
- AnalyticsDashboard.tsx
- shared/ErrorMessage.tsx
- shared/LoadingSpinner.tsx

---

## Validation Checklist

COMMON PATTERNS FIX:
[ ] prompt_common_patterns function created (separate from gotchas)
[ ] prompt_gotchas_and_tips function created (separate from patterns)
[ ] run_tier1_analysis now makes 9 calls (one for each)
[ ] run_tier2_analysis same 9 calls all Groq
[ ] analysis_task.py stores common_patterns and gotchas_and_tips separately
[ ] Frontend Architecture tab shows 4 sections, none repeated

SETUP GUIDE:
[ ] prompt_setup_guide replaced with concise version
[ ] Frontend renders Setup Guide with react-markdown
[ ] No unnecessary text in setup guide output

OPPORTUNITIES:
[ ] prompt_contribution_suggestions replaced
[ ] Max 2 fix/refactor suggestions enforced in prompt
[ ] At least 3 feature suggestions required in prompt
[ ] Re-analyze a repo and verify diverse categories

MATCHED TAB:
[ ] 'Matched' removed from TABS array
[ ] All Matched-related state removed from ResultsDashboard
[ ] Only 4 tabs remain: Summary, Architecture, Setup Guide, Opportunities

GEMINI REDIRECT:
[ ] Gemini now uses clipboard copy + open (same as Claude)
[ ] Toast message says "Context copied! Paste in Gemini (Cmd+V)"
[ ] Claude toast is more prominent

PDF FORMATTING:
[ ] markdown_to_html filter added to pdf_service.py
[ ] All three templates use |md filter for text sections
[ ] CSS added for li, h3 inside PDF templates
[ ] Download a PDF and verify no raw ## or ** visible

FULL REPORT PDF:
[ ] Button removed or fixed - only 3 working PDF types shown

ANALYTICS:
[ ] API quota section removed from dashboard

DARK MODE:
[ ] CSS variables added to index.css
[ ] html.dark class toggles variables
[ ] App.tsx adds/removes dark class on documentElement
[ ] All components use var(--bg-card) instead of white
[ ] All components use var(--text-primary) instead of #24292f
[ ] Test: toggle dark mode, all cards go dark
[ ] Test: text remains readable in dark mode

REBUILD:
[ ] docker-compose down && docker-compose up --build -d
[ ] Re-analyze a repo to get fresh data with separate patterns/gotchas
[ ] Verify all tabs load correctly

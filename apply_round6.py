import os
import re

def replace_prompts():
    filepath = 'backend/app/services/prompts.py'
    
    content = '''def prompt_project_summary(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    languages = repo_data.get("languages", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")
    commits = repo_data.get("commits", [])[:5]
    contributors = repo_data.get("contributors", [])[:3]
    file_results = ast.get("file_results", {})

    lang_text = ", ".join(languages.keys()) if languages else "Unknown"
    frameworks = ", ".join(tech_stack.get("frameworks", [])) or "none"
    imports = ", ".join(ast.get("all_imports", [])[:20]) or "none"
    recent_commits = "\\n".join(f"- {c.get('message','')}" for c in commits) or "none"
    top_contributors = ", ".join(c.get("login","") for c in contributors) or "unknown"
    key_files = ", ".join(list(file_results.keys())[:10]) or "none"

    return f"""You are a technical writer who has READ and UNDERSTOOD this entire codebase.
Write as if you know this project deeply. Be specific, direct, and confident.
NEVER use phrases like "appears to", "suggests", "may", "seems", "implies", "likely".
Only state what is DIRECTLY EVIDENT from the data below.

=== REPOSITORY DATA ===
Name: {metadata.get('full_name', 'Unknown')}
Description: {metadata.get('description', 'None')}
Primary Language: {metadata.get('language', 'Unknown')}
All Languages: {lang_text}
Detected Frameworks: {frameworks}
Stars: {metadata.get('stars', 0)} | Forks: {metadata.get('forks', 0)}
Open Issues: {metadata.get('open_issues_count', 0)}
Topics: {', '.join(metadata.get('topics', []))}
Top Contributors: {top_contributors}
Has Tests: {tech_stack.get('has_tests', False)}
Has CI/CD: {tech_stack.get('has_ci', False)}
Has Docker: {tech_stack.get('has_docker', False)}
Total Functions Found: {ast.get('total_functions', 0)}
Total Classes Found: {ast.get('total_classes', 0)}
Key Source Files: {key_files}
Key Imports/Libraries: {imports}

Recent Commits:
{recent_commits}

README (up to 3000 chars):
{readme[:3000] if readme else 'No README found.'}
=== END DATA ===

Write the summary in this EXACT markdown format:

## What It Does
Write 3-4 sentences. State exactly what this software builds or enables.
Name the specific capabilities visible in the imports and README.
Example: "LawMate is a RAG-based legal chatbot that uses ChromaDB for vector storage,
EasyOCR for document scanning, and FastAPI for the REST API backend."

## How It Works  
Write 3-4 sentences on architecture and technical flow.
Name real files, classes, and libraries from the data. Describe the actual pipeline.
Example: "The backend/ module handles API requests via FastAPI. Documents are
processed through the scripts/pipeline/ scripts, chunked and embedded into ChromaDB,
then retrieved using hybrid search in retriever.py."

## Who It's For
Write 2 sentences. Name the specific user group based on README/description.

## Project Health
Write 2 sentences. State facts: commit frequency, test presence, CI status, contributors."""

def prompt_architecture(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    structure = repo_data.get("directory_structure", {})
    tech_stack = repo_data.get("tech_stack", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")
    file_results = ast.get("file_results", {})

    imports = ast.get("all_imports", [])[:25]
    files_count = ast.get("files_analyzed", 0)
    avg_complexity = ast.get("avg_complexity", 0)
    total_functions = ast.get("total_functions", 0)
    total_classes = ast.get("total_classes", 0)

    # Build detailed file list with their classes/functions
    file_details = []
    for filepath, data in list(file_results.items())[:12]:
        classes = data.get("classes", [])
        funcs = [f["name"] for f in data.get("functions", [])[:5]]
        if classes or funcs:
            file_details.append(
                f"{filepath}: classes=[{', '.join(classes[:3])}] "
                f"functions=[{', '.join(funcs)}]"
            )

    structure_summary = []
    if isinstance(structure, dict) and "children" in structure:
        for child in structure.get("children", [])[:15]:
            name = child.get("name", "")
            type_ = child.get("type", "")
            marker = "/" if type_ == "dir" else ""
            structure_summary.append(f"- {name}{marker}")

    return f"""You are a senior software architect. Analyze this repository's architecture.
CRITICAL RULES:
- Only mention technologies FOUND IN THE IMPORTS LIST. Never invent tools.
- If a technology is not in the imports, do NOT mention it.
- Do not write intro sentences like "Welcome to..." or "Let me explain..."
- Jump directly into the content under each heading.
- Be specific: name actual files, classes, functions.

=== REPOSITORY DATA ===
Name: {metadata.get('full_name', 'Unknown')}
Language: {metadata.get('language', 'Unknown')}
Frameworks detected: {', '.join(tech_stack.get('frameworks', []))}
ALL IMPORTS FOUND: {', '.join(imports)}

Top-level directory structure:
{chr(10).join(structure_summary) or 'Not available'}

Key files and their contents:
{chr(10).join(file_details) or 'No file details'}

Code metrics: {files_count} files, {total_functions} functions, 
{total_classes} classes, avg complexity {avg_complexity}

README excerpt:
{readme[:2000] if readme else 'No README'}
=== END DATA ===

Write in this EXACT markdown format. No intro sentence. Start directly with ## Module Structure:

## Module Structure
List each top-level directory and its specific purpose based on what files are inside it.

## Key Components  
Name the most important classes and functions. Describe what each one does specifically.
Only mention things that appear in the file_results data above.

## Data Flow
Describe the actual data pipeline step by step. Use real file/function names.
Example: "User request → backend/main.py chat() → retriever.py retrieve() → 
generator.py generate_response() → response returned"

## Design Patterns
Name 2-3 specific patterns WITH EVIDENCE from the code.
Example: "Pipeline pattern: data flows through build_chunks → retrieve → generate_response"

## Where to Start
Name the SPECIFIC file a new contributor should open first and exactly why."""

def prompt_code_walkthrough(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    readme = repo_data.get("readme", "")
    file_results = ast.get("file_results", {})

    # Build rich file inventory
    file_inventory = []
    for filepath, data in list(file_results.items())[:15]:
        classes = data.get("classes", [])
        funcs = [f["name"] for f in data.get("functions", [])[:8]]
        imports = data.get("imports", [])[:8]
        file_inventory.append(
            f"\\nFILE: {filepath}\\n"
            f"  Classes: {classes}\\n"
            f"  Functions: {funcs}\\n"
            f"  Imports: {imports}"
        )

    return f"""You are an experienced engineer explaining this codebase to a new contributor.
CRITICAL RULES:
- Do NOT write intro sentences like "Welcome to...", "Let me explain...", "Happy coding!"
- Start DIRECTLY with content under the first heading
- Only reference files and functions that appear in the FILE INVENTORY below
- Be specific: quote actual function names, class names, file paths

=== FILE INVENTORY ===
{chr(10).join(file_inventory) if file_inventory else 'No files analyzed'}

README excerpt:
{readme[:1500] if readme else 'No README'}
=== END DATA ===

Write in this EXACT format. No intro. Start with ## Entry Point:

## Entry Point
Name the specific main file and function where the application starts.
Describe what it sets up and what happens first.

## Key Files Explained
For each important file, write 2-3 sentences on what it does and its key functions.
Format: **filename.py** - What it does. Key classes: X. Key functions: Y, Z.

## How the Pieces Connect
Describe how 3-4 key files call each other. Use actual function names.

## What to Modify for Common Tasks
Give 2-3 examples:
- "To add a new API endpoint: edit backend/main.py"
- "To change retrieval logic: edit backend/retrieval/retriever.py"
Name real files from the inventory."""

def prompt_patterns_and_gotchas(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    ast = repo_data.get("ast_analysis", {})
    tech_stack = repo_data.get("tech_stack", {})
    readme = repo_data.get("readme", "")
    file_results = ast.get("file_results", {})
    all_issues = ast.get("all_issues", [])[:10]

    # Collect real patterns from code
    all_imports = ast.get("all_imports", [])
    frameworks = tech_stack.get("frameworks", [])
    issues_text = "\\n".join(
        f"- [{i['file']}] {i['issue']}" for i in all_issues
    ) or "No issues detected"

    # Find repeated patterns in file structure
    file_patterns = []
    for filepath, data in list(file_results.items())[:10]:
        for func in data.get("functions", [])[:3]:
            file_patterns.append(f"{filepath}:{func['name']}")

    return f"""You are a maintainer of this project explaining its conventions.
CRITICAL RULES:
- Only describe patterns YOU CAN VERIFY from the actual code data
- Do not repeat content between Common Patterns and Gotchas sections
- Common Patterns = how code IS structured (facts)
- Gotchas = what WILL cause your PR to be rejected (warnings)
- Be specific to THIS project, not generic software advice
- No generic tips like "write tests" unless tests are actually missing here

=== PROJECT DATA ===
Name: {metadata.get('full_name', 'Unknown')}
Frameworks: {', '.join(frameworks)}
Key imports: {', '.join(all_imports[:20])}
Has tests: {tech_stack.get('has_tests', False)}
Has CI: {tech_stack.get('has_ci', False)}

Detected code issues:
{issues_text}

Sample function paths (file:function):
{', '.join(file_patterns[:20])}

README excerpt:
{readme[:1000] if readme else 'No README'}
=== END DATA ===

Write EXACTLY these two sections. Each must be DIFFERENT content. No overlap:

## Common Patterns
List 4-5 specific patterns found in THIS codebase.
Each pattern: **Pattern Name**: One sentence describing it with a real example from the code.

## Gotchas & Tips
List 4-5 specific warnings for contributors to THIS project.
Each tip: **Warning Title**: What will go wrong and how to avoid it.
Base these on the actual detected issues and project structure."""

def prompt_setup_guide(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    tech_stack = repo_data.get("tech_stack", {})
    languages = repo_data.get("languages", {})
    readme = repo_data.get("readme", "")
    ast = repo_data.get("ast_analysis", {})

    manifests = tech_stack.get("manifests_found", [])
    has_docker = tech_stack.get("has_docker", False)
    has_tests = tech_stack.get("has_tests", False)
    has_ci = tech_stack.get("has_ci", False)
    frameworks = tech_stack.get("frameworks", [])
    lang = metadata.get("language", "Unknown")
    all_imports = ast.get("all_imports", [])[:15]

    return f"""You are writing a detailed setup guide for contributors to this specific project.
CRITICAL RULES:
- Be specific to this project's actual tech stack
- Only mention tools that are confirmed by the data (imports, manifests, README)
- Give EXACT commands, not generic placeholders
- Be detailed and explain WHY each step is needed
- If Docker is present, explain how to use it

=== PROJECT DATA ===
Name: {metadata.get('full_name', 'Unknown')}
Primary language: {lang}
All languages: {', '.join(languages.keys())}
Frameworks: {', '.join(frameworks)}
Manifest files found: {', '.join(manifests)}
Has Docker: {has_docker}
Has tests: {has_tests}
Has CI: {has_ci}
Key libraries: {', '.join(all_imports)}

README excerpt (check for setup instructions):
{readme[:2500] if readme else 'No README available'}
=== END DATA ===

Write a detailed setup guide in this EXACT format:

## Prerequisites
List every tool that must be installed before starting.
For each tool, explain what it's used for in THIS project specifically.
Include version requirements if visible in the README or manifests.

## Clone and Setup
Number each step. Give exact terminal commands.
Include:
1. How to fork on GitHub
2. git clone command
3. How to install dependencies (exact pip/npm/etc commands based on manifests found)
4. How to set up environment variables (mention specific .env variables if in README)
5. Docker setup if applicable

## Verify Setup
Give 2-3 specific commands to confirm everything works.
Describe expected output for each command.

## Running Tests
Give exact command to run tests.
Explain what the test suite covers if visible from the data.

## Before You Code
Give 3-4 specific things to read or understand.
Name actual files to open, not generic advice."""

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
    all_issues = ast.get("all_issues", [])[:8]

    issues_text = "\\n".join(
        f"- [{', '.join(i.get('labels',[]))}] #{i.get('number')}: {i.get('title','')}"
        for i in issues
    ) or "No GitHub issues open"

    code_issues_text = "\\n".join(
        f"- [{i['file']}] {i['issue']}" for i in all_issues
    ) or "No code issues detected"

    # Get key files for context
    key_files = list(file_results.keys())[:10]

    return f"""You are a senior contributor to this project suggesting realistic contribution opportunities.
CRITICAL RULES:
- Suggestions must be SPECIFIC to this project's actual code and structure
- Each "what_to_do" must be 3-4 sentences explaining the actual work, not just restating the title
- Mention actual file names, function names, or class names from the project
- estimated_minutes must be realistic with AI tools (30-90 minutes for most tasks)
- Generate DIVERSE suggestions: features, docs, tests, tooling, performance
- Do NOT generate duplicate suggestions
- Return ONLY valid JSON array, no markdown, no explanation

=== PROJECT DATA ===
Repository: {metadata.get('full_name', 'Unknown')}
Description: {metadata.get('description', '')}
Language: {lang}
Frameworks: {frameworks}
Key imports: {', '.join(all_imports)}
Has tests: {has_tests}
Has CI: {has_ci}
Has Docker: {has_docker}
Key source files: {', '.join(key_files)}

GitHub Issues:
{issues_text}

Code quality issues detected:
{code_issues_text}

README excerpt:
{readme[:1500] if readme else 'No README'}
=== END DATA ===

Return a JSON array of exactly 10 unique contribution opportunities.
Each item must have ALL these fields:

[
  {{
    "title": "Short specific title (max 70 chars)",
    "what_to_do": "3-4 sentences describing EXACTLY what needs to be done. Name specific files, functions, or sections. Explain the approach and what the end result looks like.",
    "why_it_matters": "1-2 sentences on the concrete benefit to users or maintainers.",
    "files_to_look_at": ["list", "of", "actual", "filenames"],
    "category": "feature|documentation|testing|performance|tooling|refactor",
    "difficulty": 3,
    "learning_value": 7,
    "impact": 8,
    "estimated_minutes": 60,
    "difficulty_tier": "beginner|intermediate|advanced"
  }}
]

Include at minimum: 2 documentation, 2 feature, 1 testing, 1 tooling.
All filenames in files_to_look_at must be REAL files from the key source files list above."""

def prompt_contributor_guide_narrative(repo_data: dict) -> str:
    metadata = repo_data.get("metadata", {})
    issues = repo_data.get("issues", [])[:3]

    issues_text = "\\n".join(
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

    issues_text = "\\n".join(
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
'''
    with open(filepath, 'w') as f:
        f.write(content)

def fix_analysis_model():
    filepath = 'backend/app/models/analysis.py'
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'ai_suggestions: Mapped[dict] = mapped_column(JSONB, nullable=True)' not in content:
        # Import JSONB if needed, but it should be there. Let's add the field safely.
        content = content.replace(
            'is_current: Mapped[bool] = mapped_column(Boolean, default=False)',
            'ai_suggestions: Mapped[dict] = mapped_column(JSONB, nullable=True)\n    is_current: Mapped[bool] = mapped_column(Boolean, default=False)'
        )
    with open(filepath, 'w') as f:
        f.write(content)

def fix_opportunity_model():
    filepath = 'backend/app/models/opportunity.py'
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace('description: Mapped[str] = mapped_column(String(300), nullable=True)', 'description: Mapped[str] = mapped_column(String(500), nullable=True)')
    with open(filepath, 'w') as f:
        f.write(content)

def fix_analysis_task():
    filepath = 'backend/app/tasks/analysis_task.py'
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Store ai_suggestions in the analysis
    content = content.replace(
        'code_quality_metrics=combined_data.get("ast_analysis"),',
        'code_quality_metrics=combined_data.get("ast_analysis"),\n                        ai_suggestions=ai_suggestions,'
    )

    # Use what_to_do for description
    content = content.replace(
        'description=opp.get("description", "")[:300],',
        'description=(opp.get("what_to_do") or opp.get("description", ""))[:500],'
    )

    with open(filepath, 'w') as f:
        f.write(content)

def fix_results_dashboard():
    filepath = 'frontend/src/components/Analysis/ResultsDashboard.tsx'
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'const [userProfileSet, setUserProfileSet] = useState(false);' not in content:
        # Add imports and state
        content = content.replace(
            'const [matched, setMatched] = useState<any[]>([]);',
            'const [matched, setMatched] = useState<any[]>([]);\n  const [userProfileSet, setUserProfileSet] = useState(false);\n  const [localProfile, setLocalProfile] = useState({\n    skill_level: "",\n    available_hours_per_week: 0,\n    preferred_categories: [] as string[],\n  });'
        )

        old_matched_tab = '''        {tab === 'Matched' && (
          <div className="space-y-6">
            <OpportunityList opportunities={matched} showFilter={false} />
          </div>
        )}'''
        
        new_matched_tab = '''        {tab === 'Matched' && (
  <div>
    {!userProfileSet ? (
      // Profile setup form shown BEFORE matching
      <div className="max-w-md">
        <h3 className="text-base font-semibold mb-4" style={{ color: '#24292f' }}>
          Set your profile to get personalized matches
        </h3>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#24292f' }}>
              Your skill level
            </label>
            <select
              value={localProfile.skill_level}
              onChange={(e) => setLocalProfile(p => ({...p, skill_level: e.target.value}))}
              className="w-full px-3 py-2 rounded border text-sm"
              style={{ borderColor: '#d0d7de', color: '#24292f' }}
            >
              <option value="">Select level...</option>
              <option value="beginner">Beginner (0-1 years)</option>
              <option value="intermediate">Intermediate (1-3 years)</option>
              <option value="advanced">Advanced (3+ years)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#24292f' }}>
              Hours available per week
            </label>
            <input
              type="number"
              min={1}
              max={40}
              value={localProfile.available_hours_per_week || ''}
              onChange={(e) => setLocalProfile(p => ({...p, available_hours_per_week: Number(e.target.value)}))}
              placeholder="e.g. 5"
              className="w-full px-3 py-2 rounded border text-sm"
              style={{ borderColor: '#d0d7de', color: '#24292f' }}
            />
          </div>
          <button
            onClick={async () => {
              if (!localProfile.skill_level || !localProfile.available_hours_per_week) return;
              const matchedData = await getMatchedOpportunities(repoId, localProfile);
              setMatched(matchedData.top_matches || []);
              setUserProfileSet(true);
            }}
            disabled={!localProfile.skill_level || !localProfile.available_hours_per_week}
            className="px-4 py-2 rounded text-sm font-medium text-white"
            style={{ backgroundColor: '#2ea44f', opacity: (!localProfile.skill_level || !localProfile.available_hours_per_week) ? 0.6 : 1 }}
          >
            Find My Matches
          </button>
        </div>
      </div>
    ) : (
      // Show matches after profile is set
      <>
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm" style={{ color: '#57606a' }}>
            Ranked for a <strong>{localProfile.skill_level}</strong> developer
            with <strong>{localProfile.available_hours_per_week}h/week</strong>.
          </p>
          <button
            onClick={() => setUserProfileSet(false)}
            className="text-xs"
            style={{ color: '#0969da' }}
          >
            Change profile
          </button>
        </div>
        <OpportunityList opportunities={matched} showFilter={false} />
      </>
    )}
  </div>
)}'''
        content = content.replace(old_matched_tab, new_matched_tab)
        with open(filepath, 'w') as f:
            f.write(content)

def fix_opportunity_detail():
    filepath = 'frontend/src/components/Opportunities/OpportunityDetail.tsx'
    with open(filepath, 'r') as f:
        content = f.read()

    # Update what to do section
    old_what_to_do = '''          {/* What to do */}
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
          </div>'''
    
    new_what_to_do = '''          {/* What to do */}
          <div>
            <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
              What to Do
            </h3>
            <p className="text-sm" style={{ color: '#24292f', lineHeight: '1.7' }}>
              {(opp as any).what_to_do || opp.description || 'No description available.'}
            </p>
          </div>

          {/* Files to look at */}
          {(opp as any).files_to_look_at?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
                Files to Look At
              </h3>
              <div className="flex flex-wrap gap-2">
                {(opp as any).files_to_look_at.map((f: string) => (
                  <span
                    key={f}
                    className="text-xs px-2 py-1 rounded"
                    style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8',
                             fontFamily: 'monospace', color: '#24292f' }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}'''
    content = content.replace(old_what_to_do, new_what_to_do)

    # Update why it matters
    old_why_it_matters = '''          {/* Why it matters */}
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
                'This feature has been requested by users and would improve the project\\'s functionality and adoption.'}
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
          </div>'''
    new_why_it_matters = '''          {/* Why it matters */}
          <div>
            <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
              Why It Matters
            </h3>
            <p className="text-sm" style={{ color: '#57606a', lineHeight: '1.7' }}>
              {(opp as any).why_it_matters || 'Completing this improves the project quality.'}
            </p>
          </div>'''
    
    content = content.replace(old_why_it_matters, new_why_it_matters)
    with open(filepath, 'w') as f:
        f.write(content)

if __name__ == '__main__':
    replace_prompts()
    fix_analysis_model()
    fix_opportunity_model()
    fix_analysis_task()
    fix_results_dashboard()
    fix_opportunity_detail()
    print("Round 6 fixes applied successfully.")

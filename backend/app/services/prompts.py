def prompt_project_summary(repo_data: dict) -> str:
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
    recent_commits = "\n".join(f"- {c.get('message','')}" for c in commits) or "none"
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
            f"\nFILE: {filepath}\n"
            f"  Classes: {classes}\n"
            f"  Functions: {funcs}\n"
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
    all_imports = ast.get("all_imports", [])[:12]
    key_files = list(file_results.keys())[:6]

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
{readme[:800] if readme else 'No README'}

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

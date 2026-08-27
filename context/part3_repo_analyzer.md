# CONTEXT FILE: Part 3 - Repository Cloning & Code Analysis
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1 & 2

- FastAPI app running on port 8000
- PostgreSQL + Redis connected
- GitHub API service: fetch_full_repo_data(url) returns metadata, issues, contributors, languages, commits
- POST /api/repos/fetch-raw endpoint working

---

## What Part 3 Builds

Local repository analysis:
- Clone a GitHub repo to a temp directory
- Walk the directory structure
- Detect tech stack from manifest files
- Run basic AST analysis on Python files (complexity + imports)
- Detect code smells (long functions, too many parameters)
- Clean up cloned repo after analysis

New packages needed in requirements.txt:
- gitpython==3.1.43
- radon==6.0.1

Add these two lines to backend/requirements.txt.

---

## Files to Create or Modify

- backend/app/services/repo_analyzer.py    (NEW - main file for this part)
- backend/app/routes/repos.py              (MODIFY - add one new endpoint)
- backend/tests/test_repo_analyzer.py      (NEW - tests)

Do NOT modify any other files.

---

## Service: repo_analyzer.py

### backend/app/services/repo_analyzer.py

```python
import os
import ast
import shutil
import tempfile
from pathlib import Path
from git import Repo
from radon.complexity import cc_visit
from radon.metrics import mi_visit


# ─── Constants ────────────────────────────────────────────────────────────────

MANIFEST_FILES = {
    "requirements.txt": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "pyproject.toml": "Python",
    "package.json": "JavaScript/Node",
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "*.csproj": "C#",
}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".eggs", "*.egg-info",
    ".pytest_cache", ".mypy_cache", "coverage"
}

MAX_REPO_SIZE_MB = 200
MAX_FILE_SIZE_BYTES = 100_000  # Skip files larger than 100KB


# ─── Clone ────────────────────────────────────────────────────────────────────

def clone_repo(repo_url: str) -> str:
    """
    Clone a GitHub repo to a temporary directory.
    Returns the path to the cloned directory.
    Uses shallow clone (depth=1) for speed.
    Raises ValueError if repo is too large.
    """
    tmp_dir = tempfile.mkdtemp(prefix="repoinsight_")
    try:
        Repo.clone_from(
            repo_url,
            tmp_dir,
            depth=1,
            single_branch=True
        )
        # Check size
        size_mb = get_dir_size_mb(tmp_dir)
        if size_mb > MAX_REPO_SIZE_MB:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise ValueError(
                f"Repository too large ({size_mb:.1f}MB). Max is {MAX_REPO_SIZE_MB}MB."
            )
        return tmp_dir
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def cleanup_repo(path: str) -> None:
    """Delete cloned repo directory."""
    shutil.rmtree(path, ignore_errors=True)


def get_dir_size_mb(path: str) -> float:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


# ─── Directory Structure ──────────────────────────────────────────────────────

def extract_directory_structure(repo_path: str) -> dict:
    """
    Walk the repo and build a tree of folders and files.
    Ignores directories in IGNORE_DIRS.
    Returns a nested dict with keys: name, type, children (for dirs).
    Max depth: 3 levels.
    """
    def walk(path: Path, depth: int) -> dict:
        name = path.name
        if path.is_file():
            return {"name": name, "type": "file"}

        if depth > 3:
            return {"name": name, "type": "dir", "children": ["..."]}

        children = []
        try:
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for entry in entries:
                if entry.name in IGNORE_DIRS or entry.name.startswith("."):
                    continue
                children.append(walk(entry, depth + 1))
        except PermissionError:
            pass

        return {"name": name, "type": "dir", "children": children}

    root = Path(repo_path)
    result = walk(root, 0)
    return result


# ─── Tech Stack Detection ─────────────────────────────────────────────────────

def detect_tech_stack(repo_path: str) -> dict:
    """
    Detect technology stack from manifest files.
    Returns dict with:
      - languages: list of detected languages
      - frameworks: list of detected frameworks
      - manifests_found: list of manifest filenames found
      - has_tests: bool (presence of test files/dirs)
      - has_docker: bool
      - has_ci: bool
    """
    root = Path(repo_path)
    languages = set()
    frameworks = set()
    manifests_found = []

    # Check manifest files
    for filename, language in MANIFEST_FILES.items():
        if (root / filename).exists():
            languages.add(language)
            manifests_found.append(filename)

    # Detect frameworks from package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react" in deps:
                frameworks.add("React")
            if "vue" in deps:
                frameworks.add("Vue")
            if "express" in deps:
                frameworks.add("Express")
            if "next" in deps:
                frameworks.add("Next.js")
            if "fastapi" in deps or "FastAPI" in deps:
                frameworks.add("FastAPI")
        except Exception:
            pass

    # Detect frameworks from requirements.txt
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        try:
            content = req_txt.read_text().lower()
            if "django" in content:
                frameworks.add("Django")
            if "fastapi" in content:
                frameworks.add("FastAPI")
            if "flask" in content:
                frameworks.add("Flask")
            if "sqlalchemy" in content:
                frameworks.add("SQLAlchemy")
            if "celery" in content:
                frameworks.add("Celery")
            if "pytest" in content:
                frameworks.add("pytest")
        except Exception:
            pass

    # Check for tests
    test_indicators = ["tests/", "test/", "spec/", "__tests__/"]
    has_tests = any((root / t.rstrip("/")).exists() for t in test_indicators)

    # Check for Docker
    has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()

    # Check for CI
    has_ci = (
        (root / ".github" / "workflows").exists() or
        (root / ".gitlab-ci.yml").exists() or
        (root / ".circleci").exists() or
        (root / "Jenkinsfile").exists()
    )

    return {
        "languages": sorted(list(languages)),
        "frameworks": sorted(list(frameworks)),
        "manifests_found": manifests_found,
        "has_tests": has_tests,
        "has_docker": has_docker,
        "has_ci": has_ci,
    }


# ─── AST Analysis (Python only) ──────────────────────────────────────────────

def analyze_python_file(file_path: str) -> dict:
    """
    Analyze a single Python file using AST and radon.
    Returns:
      - functions: list of {name, line, args_count, is_complex}
      - imports: list of imported module names
      - classes: list of class names
      - complexity_scores: list of {name, complexity, rank}
      - issues: list of detected code smell strings
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    if len(content.encode()) > MAX_FILE_SIZE_BYTES:
        return {}

    result = {
        "functions": [],
        "imports": [],
        "classes": [],
        "complexity_scores": [],
        "issues": []
    }

    # AST parsing
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        # Collect imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module.split(".")[0])

        # Collect classes
        elif isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)

        # Collect functions and detect smells
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args_count = len(node.args.args)
            body_lines = (node.end_lineno - node.lineno) if hasattr(node, 'end_lineno') else 0

            func_info = {
                "name": node.name,
                "line": node.lineno,
                "args_count": args_count,
                "body_lines": body_lines,
            }
            result["functions"].append(func_info)

            # Detect smells
            if args_count > 5:
                result["issues"].append(
                    f"Function '{node.name}' has too many parameters ({args_count})"
                )
            if body_lines > 50:
                result["issues"].append(
                    f"Function '{node.name}' is too long ({body_lines} lines)"
                )

    # Radon complexity
    try:
        cc_results = cc_visit(content)
        for item in cc_results:
            result["complexity_scores"].append({
                "name": item.name,
                "complexity": item.complexity,
                "rank": item.rank,
            })
            if item.complexity > 10:
                result["issues"].append(
                    f"High complexity in '{item.name}' (score: {item.complexity})"
                )
    except Exception:
        pass

    # Deduplicate imports
    result["imports"] = sorted(list(set(result["imports"])))

    return result


def analyze_all_python_files(repo_path: str, max_files: int = 30) -> dict:
    """
    Find all .py files in the repo and analyze each one.
    Skips files in IGNORE_DIRS.
    Returns aggregated results:
      - files_analyzed: int
      - all_issues: list of {file, issue}
      - all_imports: list of unique imports across project
      - avg_complexity: float
      - total_functions: int
      - total_classes: int
      - file_results: dict of {relative_path: analysis_result}
    """
    root = Path(repo_path)
    py_files = []

    for path in root.rglob("*.py"):
        # Skip ignored dirs
        parts = set(path.parts)
        if parts & IGNORE_DIRS:
            continue
        py_files.append(path)
        if len(py_files) >= max_files:
            break

    all_issues = []
    all_imports = set()
    all_complexity = []
    total_functions = 0
    total_classes = 0
    file_results = {}

    for py_file in py_files:
        rel_path = str(py_file.relative_to(root))
        analysis = analyze_python_file(str(py_file))

        if not analysis:
            continue

        file_results[rel_path] = analysis

        for issue in analysis.get("issues", []):
            all_issues.append({"file": rel_path, "issue": issue})

        all_imports.update(analysis.get("imports", []))

        for score in analysis.get("complexity_scores", []):
            all_complexity.append(score["complexity"])

        total_functions += len(analysis.get("functions", []))
        total_classes += len(analysis.get("classes", []))

    avg_complexity = (
        round(sum(all_complexity) / len(all_complexity), 2)
        if all_complexity else 0.0
    )

    return {
        "files_analyzed": len(file_results),
        "all_issues": all_issues[:50],  # cap at 50
        "all_imports": sorted(list(all_imports)),
        "avg_complexity": avg_complexity,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "file_results": file_results,
    }


# ─── Master Analysis Function ─────────────────────────────────────────────────

def analyze_repository_locally(repo_url: str) -> dict:
    """
    Master function:
    1. Clones repo
    2. Extracts directory structure
    3. Detects tech stack
    4. Runs AST analysis on Python files
    5. Cleans up
    6. Returns combined result

    Always cleans up even if analysis fails.
    """
    repo_path = None
    try:
        repo_path = clone_repo(repo_url)

        structure = extract_directory_structure(repo_path)
        tech_stack = detect_tech_stack(repo_path)
        ast_analysis = analyze_all_python_files(repo_path)

        return {
            "status": "success",
            "directory_structure": structure,
            "tech_stack": tech_stack,
            "ast_analysis": ast_analysis,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "directory_structure": {},
            "tech_stack": {},
            "ast_analysis": {},
        }
    finally:
        if repo_path:
            cleanup_repo(repo_path)
```

---

## Route Update

### Modify backend/app/routes/repos.py

Add this new endpoint. Do NOT remove the existing /repos/fetch-raw endpoint.

```python
from app.services.repo_analyzer import analyze_repository_locally

@router.post("/repos/analyze-local")
async def analyze_repo_locally(request: RepoURLRequest):
    if not is_valid_github_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    result = analyze_repository_locally(request.url)
    return result
```

Note: This endpoint is synchronous-feeling but acceptable for now.
Async job queue (Celery) will wrap this in Part 9.

---

## Tests

### backend/tests/test_repo_analyzer.py

```python
import os
import tempfile
import pytest
from pathlib import Path
from app.services.repo_analyzer import (
    extract_directory_structure,
    detect_tech_stack,
    analyze_python_file,
    get_dir_size_mb,
    cleanup_repo,
)


@pytest.fixture
def sample_python_project(tmp_path):
    """Create a minimal fake Python project for testing."""
    # Create files
    (tmp_path / "requirements.txt").write_text("fastapi==0.111.0\ncelery==5.4.0\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "workflows").mkdir()
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")

    src = tmp_path / "app"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "main.py").write_text(
        "import os\nimport sys\n\ndef simple(a, b):\n    return a + b\n\n"
        "def too_many_args(a, b, c, d, e, f, g):\n    pass\n"
    )

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")

    return tmp_path


def test_extract_directory_structure(sample_python_project):
    result = extract_directory_structure(str(sample_python_project))
    assert result["type"] == "dir"
    names = [c["name"] for c in result["children"]]
    assert "app" in names
    assert "tests" in names
    assert ".github" not in names  # hidden dirs skipped


def test_detect_tech_stack_python(sample_python_project):
    result = detect_tech_stack(str(sample_python_project))
    assert "Python" in result["languages"]
    assert result["has_docker"] is True
    assert result["has_ci"] is True
    assert result["has_tests"] is True


def test_detect_frameworks_from_requirements(sample_python_project):
    result = detect_tech_stack(str(sample_python_project))
    assert "FastAPI" in result["frameworks"]
    assert "Celery" in result["frameworks"]


def test_analyze_python_file_imports(sample_python_project):
    main_py = str(sample_python_project / "app" / "main.py")
    result = analyze_python_file(main_py)
    assert "os" in result["imports"]
    assert "sys" in result["imports"]


def test_analyze_python_file_functions(sample_python_project):
    main_py = str(sample_python_project / "app" / "main.py")
    result = analyze_python_file(main_py)
    names = [f["name"] for f in result["functions"]]
    assert "simple" in names
    assert "too_many_args" in names


def test_detect_too_many_params_issue(sample_python_project):
    main_py = str(sample_python_project / "app" / "main.py")
    result = analyze_python_file(main_py)
    issues = result["issues"]
    assert any("too_many_args" in i for i in issues)


def test_get_dir_size_mb(sample_python_project):
    size = get_dir_size_mb(str(sample_python_project))
    assert size >= 0
    assert size < 1  # small test project


def test_cleanup_removes_directory(tmp_path):
    test_dir = str(tmp_path / "test_clone")
    os.makedirs(test_dir)
    assert os.path.exists(test_dir)
    cleanup_repo(test_dir)
    assert not os.path.exists(test_dir)
```

---

## Validation Checklist

After building, verify all of these:

[ ] radon and gitpython added to requirements.txt
[ ] backend/app/services/repo_analyzer.py created with all functions
[ ] backend/app/routes/repos.py has new POST /api/repos/analyze-local endpoint
[ ] Old /api/repos/fetch-raw endpoint still works
[ ] All 8 tests pass: pytest backend/tests/test_repo_analyzer.py
[ ] This curl command returns success with structure, tech_stack, ast_analysis:

curl -X POST http://localhost:8000/api/repos/analyze-local \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/psf/requests"}'

[ ] Response includes:
    - directory_structure with name and children
    - tech_stack with languages containing "Python"
    - ast_analysis with files_analyzed > 0
    - ast_analysis with avg_complexity > 0

Note: This endpoint takes 30-60 seconds (cloning takes time). That is expected.

---

## What Part 4 Will Cover

- Full database models (all tables)
- Alembic migrations
- Storing analysis results in PostgreSQL

Do NOT add database storage in Part 3.
Do NOT add LLM calls in Part 3.
Do NOT add Celery jobs in Part 3.

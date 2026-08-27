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

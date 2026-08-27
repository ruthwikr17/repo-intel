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

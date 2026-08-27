import pytest
from app.services.github_service import parse_repo_url
from app.utils.validators import is_valid_github_url

def test_parse_valid_url():
    owner, repo = parse_repo_url("https://github.com/django/django-rest-framework")
    assert owner == "django"
    assert repo == "django-rest-framework"

def test_parse_url_with_trailing_slash():
    owner, repo = parse_repo_url("https://github.com/pallets/flask/")
    assert owner == "pallets"
    assert repo == "flask"

def test_parse_url_with_dot_git():
    owner, repo = parse_repo_url("https://github.com/psf/requests.git")
    assert owner == "psf"
    assert repo == "requests"

def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_repo_url("https://gitlab.com/user/repo")

def test_parse_non_url_raises():
    with pytest.raises(ValueError):
        parse_repo_url("not-a-url")

def test_validator_valid_url():
    assert is_valid_github_url("https://github.com/django/django") is True

def test_validator_invalid_url():
    assert is_valid_github_url("https://gitlab.com/user/repo") is False

def test_validator_empty_string():
    assert is_valid_github_url("") is False

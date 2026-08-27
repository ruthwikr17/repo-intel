# CONTEXT FILE: Part 4 - Database Models & Alembic Migrations
# Project: RepoInsight
# Read this entire file before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-3

- Part 1: FastAPI, PostgreSQL, Redis, Docker, health endpoint
- Part 2: GitHub API service, POST /api/repos/fetch-raw
- Part 3: Repo cloning, AST analysis, POST /api/repos/analyze-local
- Scaffold models exist: repository.py, api_log.py (minimal, need full implementation)

---

## What Part 4 Builds

Complete SQLAlchemy models for all database tables.
Alembic migration setup and initial migration.

---

## Files to Create or Modify

- backend/app/models/repository.py     (REPLACE scaffold with full model)
- backend/app/models/analysis.py       (REPLACE empty file with full model)
- backend/app/models/user.py           (REPLACE empty file with full model)
- backend/app/models/api_log.py        (REPLACE scaffold with full model)
- backend/app/models/opportunity.py    (NEW)
- backend/app/models/contribution.py   (NEW)
- backend/app/models/pdf_report.py     (NEW)
- backend/app/models/__init__.py       (MODIFY - import all models)
- backend/app/database.py              (MODIFY - add create_tables function)
- backend/app/main.py                  (MODIFY - call create_tables on startup)
- backend/alembic.ini                  (NEW)
- backend/alembic/env.py               (NEW)
- backend/alembic/versions/.gitkeep    (NEW)
- backend/tests/test_models.py         (NEW)

---

## Full Model Definitions

### backend/app/models/user.py

```python
from sqlalchemy import String, Integer, Boolean, DateTime, func, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Profile
    skill_level: Mapped[str] = mapped_column(String(20), nullable=True)  # beginner/intermediate/advanced
    primary_language: Mapped[str] = mapped_column(String(50), nullable=True)
    interests: Mapped[dict] = mapped_column(JSONB, nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=True)
    available_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=True)

    # Stats
    repos_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    contributions_made: Mapped[int] = mapped_column(Integer, default=0)
    prs_merged: Mapped[int] = mapped_column(Integer, default=0)
    days_streak: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    contributions: Mapped[list] = relationship("UserContribution", back_populates="user")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="user")
```

---

### backend/app/models/repository.py

```python
from sqlalchemy import String, Integer, Boolean, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)

    # GitHub metadata
    language: Mapped[str] = mapped_column(String(50), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[dict] = mapped_column(JSONB, nullable=True)
    license: Mapped[str] = mapped_column(String(100), nullable=True)

    # Analysis status
    analysis_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending/analyzing/completed/failed
    last_analyzed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Cached raw data from GitHub API (stored to avoid re-fetching)
    cached_github_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    cached_until: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    analyses: Mapped[list] = relationship("RepositoryAnalysis", back_populates="repository")
    opportunities: Mapped[list] = relationship("Opportunity", back_populates="repository")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="repository")
```

---

### backend/app/models/analysis.py

```python
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False, index=True
    )

    # LLM tier used
    quality_tier: Mapped[str] = mapped_column(String(20), nullable=True)  # HIGH/MEDIUM
    apis_used: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # AI-generated text fields
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    architecture_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    code_walkthrough: Mapped[str] = mapped_column(Text, nullable=True)
    common_patterns: Mapped[str] = mapped_column(Text, nullable=True)
    gotchas_and_tips: Mapped[str] = mapped_column(Text, nullable=True)
    setup_guide: Mapped[str] = mapped_column(Text, nullable=True)

    # Data from GitHub API (stored as JSON)
    tech_stack: Mapped[dict] = mapped_column(JSONB, nullable=True)
    directory_structure: Mapped[dict] = mapped_column(JSONB, nullable=True)
    open_issues: Mapped[dict] = mapped_column(JSONB, nullable=True)
    contributors: Mapped[dict] = mapped_column(JSONB, nullable=True)
    commits: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Code quality metrics from AST analysis
    code_quality_metrics: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Example: {avg_complexity, files_analyzed, total_functions, all_issues}

    # Flags
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="analyses")
    opportunities: Mapped[list] = relationship("Opportunity", back_populates="analysis")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="analysis")
```

---

### backend/app/models/opportunity.py

```python
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repository_analyses.id"), nullable=False
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False, index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    # bug / feature / documentation / refactor / testing / dependency

    # GitHub link
    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=True)
    github_issue_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Scores (1-10 each)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=True)
    learning_value: Mapped[int] = mapped_column(Integer, nullable=True)
    impact: Mapped[int] = mapped_column(Integer, nullable=True)
    feasibility: Mapped[int] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Estimates
    estimated_hours: Mapped[int] = mapped_column(Integer, nullable=True)
    difficulty_tier: Mapped[str] = mapped_column(String(20), nullable=True)
    # beginner / intermediate / advanced

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    analysis: Mapped["RepositoryAnalysis"] = relationship(
        "RepositoryAnalysis", back_populates="opportunities"
    )
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="opportunities"
    )
    contributions: Mapped[list] = relationship(
        "UserContribution", back_populates="opportunity"
    )
```

---

### backend/app/models/contribution.py

```python
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserContribution(Base):
    __tablename__ = "user_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False
    )
    opportunity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("opportunities.id"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(String(30), default="interested")
    # interested / started / pr_submitted / merged / abandoned

    # PR details
    branch_name: Mapped[str] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str] = mapped_column(String(512), nullable=True)
    pr_title: Mapped[str] = mapped_column(String(255), nullable=True)

    # Timestamps
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    pr_submitted_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    merged_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Metrics
    hours_spent: Mapped[float] = mapped_column(Float, nullable=True)
    lines_changed: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contributions")
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity", back_populates="contributions"
    )
```

---

### backend/app/models/api_log.py

```python
from sqlalchemy import String, Integer, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project: Mapped[str] = mapped_column(String(50), nullable=True)
    calls_used: Mapped[int] = mapped_column(Integer, default=1)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)
    analysis_id: Mapped[int] = mapped_column(Integer, nullable=True)
    date: Mapped[Date] = mapped_column(Date, server_default=func.current_date(), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
```

---

### backend/app/models/pdf_report.py

```python
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PdfReport(Base):
    __tablename__ = "pdf_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False
    )
    analysis_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repository_analyses.id"), nullable=True
    )

    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # contributor_guide / code_quality / executive_summary / comparison

    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    share_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)

    generated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pdf_reports")
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="pdf_reports"
    )
    analysis: Mapped["RepositoryAnalysis"] = relationship(
        "RepositoryAnalysis", back_populates="pdf_reports"
    )
```

---

### backend/app/models/__init__.py

```python
from app.models.user import User
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.models.contribution import UserContribution
from app.models.api_log import ApiLog
from app.models.pdf_report import PdfReport

__all__ = [
    "User",
    "Repository",
    "RepositoryAnalysis",
    "Opportunity",
    "UserContribution",
    "ApiLog",
    "PdfReport",
]
```

---

### Modify backend/app/database.py

Add create_tables function at the bottom:

```python
async def create_tables():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        from app.models import (
            User, Repository, RepositoryAnalysis,
            Opportunity, UserContribution, ApiLog, PdfReport
        )
        await conn.run_sync(Base.metadata.create_all)
```

---

### Modify backend/app/main.py

Update startup event to call create_tables:

```python
from app.database import create_tables

@app.on_event("startup")
async def startup():
    await create_tables()
    print(f"RepoInsight API starting in {settings.app_env} mode")
```

---

## Alembic Setup

### backend/alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

### backend/alembic/env.py

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.config import get_settings
import app.models  # noqa: F401 - ensures all models are imported

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

### backend/alembic/versions/.gitkeep

Empty file. Just create it.

---

## Tests

### backend/tests/test_models.py

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import (
    User, Repository, RepositoryAnalysis,
    Opportunity, UserContribution, ApiLog, PdfReport
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user = User(username="testuser", skill_level="intermediate")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.id is not None
    assert user.username == "testuser"
    assert user.repos_analyzed == 0


@pytest.mark.asyncio
async def test_create_repository(db_session: AsyncSession):
    repo = Repository(
        owner="django",
        name="django-rest-framework",
        full_name="django/django-rest-framework",
        url="https://github.com/django/django-rest-framework",
        stars=25000,
        language="Python",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    assert repo.id is not None
    assert repo.analysis_status == "pending"
    assert repo.stars == 25000


@pytest.mark.asyncio
async def test_create_api_log(db_session: AsyncSession):
    log = ApiLog(
        model="gemini-3.6-flash",
        project="project-a",
        calls_used=4,
        tokens_input=1000,
        tokens_output=2000,
        status="success"
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    assert log.id is not None
    assert log.model == "gemini-3.6-flash"
    assert log.calls_used == 4


@pytest.mark.asyncio
async def test_create_analysis(db_session: AsyncSession):
    repo = Repository(
        owner="psf",
        name="requests",
        full_name="psf/requests",
        url="https://github.com/psf/requests",
    )
    db_session.add(repo)
    await db_session.commit()

    analysis = RepositoryAnalysis(
        repo_id=repo.id,
        quality_tier="HIGH",
        summary="A simple HTTP library."
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)
    assert analysis.id is not None
    assert analysis.is_current is True
```

Note: Tests use SQLite in-memory database. Add aiosqlite to requirements.txt:
aiosqlite==0.20.0

---

## Validation Checklist

[ ] aiosqlite added to requirements.txt
[ ] All 7 model files created with full content
[ ] backend/app/models/__init__.py imports all models
[ ] backend/app/database.py has create_tables() function
[ ] backend/app/main.py calls create_tables() on startup
[ ] backend/alembic.ini created
[ ] backend/alembic/env.py created
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d
[ ] On startup logs show no errors
[ ] GET /api/health still returns connected
[ ] All 4 model tests pass: pytest backend/tests/test_models.py

Tables auto-created on startup (no manual migration needed for dev).
Alembic is configured for production migrations later.

---

## What Part 5 Will Cover

- Gemini 2.5 Pro API integration (both projects)
- Groq Llama 3.3 API integration
- Prompt templates for all 8 LLM calls
- LLM service that runs all calls in parallel

Do NOT add LLM calls in Part 4.
Do NOT add Celery in Part 4.

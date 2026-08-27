# CONTEXT FILE: Part 1 - Project Setup & Structure
# Project: RepoInsight
# Hand this file to your AI model before asking it to do anything.
# The model must read this entire file first, then follow the instructions.

---

## What We Are Building

RepoInsight is a full-stack web application that:
- Accepts a GitHub repository URL from a user
- Analyzes the repository (code structure, issues, tech stack)
- Uses AI (Gemini 2.5 Pro + Groq Llama 3.3) to generate insights
- Returns 12 structured components of analysis
- Generates downloadable PDF reports
- Matches developers to contribution opportunities based on skill level

This is Part 1: Project Setup only.
Do NOT build any features yet. Only set up the project structure.

---

## Tech Stack (Non-Negotiable)

Backend:
- Python 3.11+
- FastAPI (web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Redis (cache + task queue)
- Celery (async jobs)
- Pydantic v2 (data validation)
- python-dotenv (environment variables)

Frontend:
- React 18 with TypeScript
- Tailwind CSS
- Axios (API calls)
- Vite (build tool)

Infrastructure:
- Docker + Docker Compose
- GitHub Actions (CI/CD, set up later)

---

## Exact Folder Structure to Create

repoinsight/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # All settings, loaded from .env
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User model (empty for now, scaffold only)
│   │   │   ├── repository.py        # Repository model (empty for now)
│   │   │   ├── analysis.py          # Analysis model (empty for now)
│   │   │   └── api_log.py           # API usage log model (empty for now)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── health.py            # GET /health endpoint only
│   │   ├── services/
│   │   │   └── __init__.py          # Empty, services added in later parts
│   │   └── utils/
│   │       └── __init__.py          # Empty, utilities added later
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py           # Test the health endpoint
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── components/
│   │       └── .gitkeep
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── docker-compose.yml
├── .gitignore
└── README.md

---

## File Contents to Generate

### backend/requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.3.0
python-dotenv==1.0.1
celery==5.4.0
redis==5.0.4
httpx==0.27.0
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0

---

### backend/.env.example
# Copy this to .env and fill in values
# NEVER commit .env to git

APP_NAME=RepoInsight
APP_ENV=development
APP_PORT=8000
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://repoinsight:repoinsight@localhost:5432/repoinsight

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub API
GITHUB_TOKEN=your_github_personal_access_token_here

# Gemini API (Two projects for dual quota)
GEMINI_API_KEY_PROJECT_A=your_gemini_project_a_key_here
GEMINI_API_KEY_PROJECT_B=your_gemini_project_b_key_here

# Groq API
GROQ_API_KEY=your_groq_api_key_here

# Security
SECRET_KEY=change_this_to_a_random_secret_key_min_32_chars

---

### backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "RepoInsight"
    app_env: str = "development"
    app_port: int = 8000
    debug: bool = True

    database_url: str
    redis_url: str

    github_token: str

    gemini_api_key_project_a: str
    gemini_api_key_project_b: str
    groq_api_key: str

    secret_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

---

### backend/app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

---

### backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes.health import router as health_router

settings = get_settings()

app = FastAPI(
    title="RepoInsight API",
    description="Repository Analysis and Contribution Matching Platform",
    version="1.0.0",
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["health"])

@app.on_event("startup")
async def startup():
    print(f"RepoInsight API starting in {settings.app_env} mode")

@app.on_event("shutdown")
async def shutdown():
    print("RepoInsight API shutting down")

---

### backend/app/routes/health.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app": "RepoInsight",
        "database": db_status
    }

---

### backend/app/models/repository.py
# Scaffold only. Full model built in Part 4.

from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

---

### backend/app/models/api_log.py
# Scaffold only. Full model built in Part 4.

from sqlalchemy import String, Integer, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    project: Mapped[str] = mapped_column(String(50), nullable=True)
    calls_used: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

---

### backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

---

### docker-compose.yml

version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://repoinsight:repoinsight@db:5432/repoinsight
      REDIS_URL: redis://cache:6379/0
    env_file:
      - ./backend/.env
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    volumes:
      - ./backend:/app
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: repoinsight
      POSTGRES_USER: repoinsight
      POSTGRES_PASSWORD: repoinsight
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U repoinsight"]
      interval: 5s
      timeout: 5s
      retries: 5

  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:

---

### backend/tests/test_health.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "RepoInsight"
    assert "database" in data

---

### frontend/package.json

{
  "name": "repoinsight-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "axios": "^1.7.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.4.5",
    "vite": "^5.3.1",
    "tailwindcss": "^3.4.4",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39"
  }
}

---

### frontend/src/App.tsx

function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900">RepoInsight</h1>
        <p className="mt-2 text-gray-600">Repository Analysis Platform</p>
        <p className="mt-4 text-sm text-green-600">Setup complete. Ready to build.</p>
      </div>
    </div>
  )
}

export default App

---

### .gitignore

# Environment
.env
*.env

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/

# Node
node_modules/
dist/
.vite/

# Storage
*.pdf
/storage/

# IDE
.vscode/
.idea/

---

### README.md

# RepoInsight

Full-Stack Repository Analysis System with AI-Powered Matching Engine for Open Source Contributors.

## Quick Start

1. Copy env file: `cp backend/.env.example backend/.env`
2. Fill in API keys in `backend/.env`
3. Run: `docker-compose up`
4. API: http://localhost:8000
5. Docs: http://localhost:8000/docs
6. Frontend: `cd frontend && npm install && npm run dev`

## Project Structure
See CONTEXT_PART1_PROJECT_SETUP.md for full details.

---

## Instructions for AI Model (Gemini Flash)

Read everything above, then:

Step 1: Create every file listed in the folder structure with exact content shown
Step 2: For files with scaffold-only note, create with shown minimal content only
Step 3: Do not add extra features or files not listed
Step 4: Do not modify the tech stack or swap any library
Step 5: After creating all files, run this validation checklist

---

## Validation Checklist (Model Must Verify Before Finishing)

[ ] All folders created exactly as shown in folder structure
[ ] backend/requirements.txt exists with all packages listed
[ ] backend/.env.example exists with all keys listed
[ ] backend/app/config.py loads settings from .env using pydantic-settings
[ ] backend/app/database.py has async SQLAlchemy engine setup
[ ] backend/app/main.py has FastAPI app with CORS and health route included
[ ] backend/app/routes/health.py has GET /api/health endpoint
[ ] backend/app/models/ has 4 files: user.py, repository.py, analysis.py, api_log.py
[ ] docker-compose.yml has backend, db (postgres), and cache (redis) services
[ ] docker-compose.yml has healthchecks on db and cache
[ ] backend/Dockerfile builds correctly
[ ] frontend/src/App.tsx renders basic RepoInsight page
[ ] .gitignore excludes .env files
[ ] No .env file committed (only .env.example)

---

## What Part 2 Will Cover

Once Part 1 is complete and validated, Part 2 will add:
- GitHub API client (fetch repo metadata, issues, commits)
- GitHub token authentication
- Rate limit handling
- API response models

Do not build any of this in Part 1.

---

## Questions the Model Should NOT Ask

Do not ask which database to use. Answer: PostgreSQL.
Do not ask which frontend framework. Answer: React with TypeScript.
Do not suggest alternatives. Follow the spec exactly.
Do not add authentication. That is Part 7.
Do not add any LLM calls. That is Part 5.

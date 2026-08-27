import os

files = {
    "backend/requirements.txt": """fastapi==0.111.0
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
pytest-asyncio==0.23.7""",

    "backend/.env.example": """# Copy this to .env and fill in values
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
SECRET_KEY=change_this_to_a_random_secret_key_min_32_chars""",

    "backend/app/__init__.py": "",

    "backend/app/config.py": """from pydantic_settings import BaseSettings
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
    return Settings()""",

    "backend/app/database.py": """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
            await session.close()""",

    "backend/app/main.py": """from fastapi import FastAPI
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
    allow_origins=["http://localhost:5173"],
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
    print("RepoInsight API shutting down")""",

    "backend/app/routes/__init__.py": "",

    "backend/app/routes/health.py": """from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app": "RepoInsight",
        "database": db_status
    }""",

    "backend/app/models/__init__.py": "",
    "backend/app/models/user.py": "",
    "backend/app/models/analysis.py": "",

    "backend/app/models/repository.py": """from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())""",

    "backend/app/models/api_log.py": """from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    project: Mapped[str] = mapped_column(String(50), nullable=True)
    calls_used: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())""",

    "backend/app/services/__init__.py": "",
    "backend/app/utils/__init__.py": "",
    "backend/tests/__init__.py": "",

    "backend/tests/test_health.py": """import pytest
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
    assert "database" in data""",

    "backend/Dockerfile": """FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    gcc \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]""",

    "docker-compose.yml": """version: "3.8"

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
  redis_data:""",

    "frontend/src/App.tsx": """function App() {
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

export default App""",

    "frontend/src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)""",

    "frontend/src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;""",

    "frontend/src/components/.gitkeep": "",

    "frontend/index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RepoInsight</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>""",

    "frontend/package.json": """{
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
}""",

    "frontend/tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}""",

    "frontend/vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})""",

    "frontend/tailwind.config.js": """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}""",

    "frontend/postcss.config.js": """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}""",

    ".gitignore": """# Environment
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
.idea/""",

    "README.md": """# RepoInsight

Full-Stack Repository Analysis System with AI-Powered Matching Engine for Open Source Contributors.

## Quick Start

1. Copy env: `cp backend/.env.example backend/.env`
2. Fill in API keys in `backend/.env`
3. Run services: `docker-compose up -d`
4. API: http://localhost:8000/api/health
5. API Docs: http://localhost:8000/docs
6. Frontend: `cd frontend && npm install && npm run dev`
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w") as f:
        f.write(content)

print("All files created successfully.")
# CONTEXT FILE: Part 13 - Docker Production & Deployment
# Project: RepoInsight
# Read the existing codebase before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-12

Complete application:
- Backend: FastAPI + Celery + PostgreSQL + Redis
- Frontend: React + TypeScript + Tailwind
- AI: Gemini 2.5 Pro + Groq Llama 3.3 (tier selection)
- PDF: Weasyprint (3 report types)
- All endpoints working locally via docker-compose

---

## What Part 13 Builds

- Production Dockerfile (optimized, no --reload)
- Separate frontend Dockerfile
- Production docker-compose.yml
- GitHub Actions CI/CD pipeline
- Railway deployment configuration
- Environment variable documentation

---

## Files to Create or Modify

- backend/Dockerfile                    (MODIFY - production optimized)
- frontend/Dockerfile                   (NEW)
- docker-compose.prod.yml               (NEW)
- .github/workflows/deploy.yml          (NEW)
- railway.toml                          (NEW)
- .env.production.example               (NEW)
- backend/app/routes/health.py          (MODIFY - enhanced health check)

---

## Production Backend Dockerfile

### backend/Dockerfile (REPLACE existing)

```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Create PDF output directory
RUN mkdir -p /tmp/repoinsight_pdfs

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Production: no --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--log-level", "info"]
```

---

## Frontend Dockerfile

### frontend/Dockerfile (NEW)

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Production: serve with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## Nginx Config

### frontend/nginx.conf (NEW)

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Proxy API calls to backend
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    # React SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Production Docker Compose

### docker-compose.prod.yml (NEW)

```yaml
version: "3.8"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

  db:
    image: postgres:15-alpine
    env_file:
      - .env.production
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  cache:
    image: redis:7-alpine
    volumes:
      - redis_data_prod:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

volumes:
  postgres_data_prod:
  redis_data_prod:
```

---

## Production Environment File

### .env.production.example (NEW)

```bash
# Copy to .env.production and fill in real values
# NEVER commit .env.production to git

# App
APP_NAME=RepoInsight
APP_ENV=production
APP_PORT=8000
DEBUG=false

# Database (Railway provides this automatically)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
POSTGRES_USER=repoinsight
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=repoinsight

# Redis (Railway provides this automatically)
REDIS_URL=redis://host:6379/0

# GitHub API
GITHUB_TOKEN=your_github_token_here

# Gemini (two projects for dual quota)
GEMINI_API_KEY_PROJECT_A=your_gemini_project_a_key
GEMINI_API_KEY_PROJECT_B=your_gemini_project_b_key

# Groq
GROQ_API_KEY=your_groq_api_key

# Security
SECRET_KEY=generate_with_openssl_rand_hex_32
```

---

## Enhanced Health Check

### Modify backend/app/routes/health.py (REPLACE)

```python
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis
from app.database import get_db
from app.config import get_settings

settings = get_settings()
router = APIRouter()
START_TIME = time.time()


async def get_redis():
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Redis check
    try:
        await redis.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    uptime_seconds = int(time.time() - START_TIME)

    return {
        "status": "ok" if db_status == "connected" and redis_status == "connected" else "degraded",
        "app": "RepoInsight",
        "environment": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
    }
```

---

## GitHub Actions CI/CD

### .github/workflows/deploy.yml (NEW)

Create folder .github/workflows/ at project root first.

```yaml
name: Deploy RepoInsight

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install aiosqlite pytest-asyncio

      - name: Run tests
        env:
          DATABASE_URL: sqlite+aiosqlite:///:memory:
          REDIS_URL: redis://localhost:6379/0
          GITHUB_TOKEN: fake_token
          GEMINI_API_KEY_PROJECT_A: fake_key
          GEMINI_API_KEY_PROJECT_B: fake_key
          GROQ_API_KEY: fake_key
          SECRET_KEY: testsecretkey123456789012345678
        run: |
          cd backend
          pytest tests/ -v --ignore=tests/test_routes.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --detach
```

---

## Railway Config

### railway.toml (NEW)

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/api/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

---

## Deployment Steps for Railway

These are manual steps, not code. Follow in order:

Step 1: Push code to GitHub
```bash
git add .
git commit -m "feat: complete RepoInsight v1.0"
git push origin main
```

Step 2: Create Railway account
- Go to railway.app
- Sign up with GitHub
- Click "New Project" → "Deploy from GitHub repo"
- Select your repo

Step 3: Add services in Railway dashboard
- Add PostgreSQL service (click +, select PostgreSQL)
- Add Redis service (click +, select Redis)
- Railway auto-sets DATABASE_URL and REDIS_URL

Step 4: Set environment variables in Railway
- Go to your backend service → Variables
- Add all variables from .env.production.example
- Railway PostgreSQL and Redis URLs are auto-populated

Step 5: Add Celery worker service
- In Railway: New Service → GitHub Repo (same repo)
- Set start command: celery -A app.worker.celery_app worker --loglevel=info
- Add same environment variables

Step 6: Deploy frontend separately
- Railway: New Service → GitHub Repo
- Set root directory: frontend
- Railway auto-detects Node.js

Step 7: Get Railway token for CI/CD
- Railway dashboard → Account → Tokens
- Copy token
- GitHub repo → Settings → Secrets → RAILWAY_TOKEN

---

## Validation Checklist

[ ] backend/Dockerfile updated (includes weasyprint system deps, no --reload)
[ ] frontend/Dockerfile created
[ ] frontend/nginx.conf created
[ ] docker-compose.prod.yml created
[ ] .env.production.example created
[ ] .github/workflows/deploy.yml created (create .github/workflows/ folder first)
[ ] railway.toml created
[ ] backend/app/routes/health.py updated with Redis check + uptime

Local production test:
```bash
cp .env.production.example .env.production
# Fill in real values in .env.production
docker-compose -f docker-compose.prod.yml up --build -d
curl http://localhost:8000/api/health
```

Expected health response:
{
  "status": "ok",
  "app": "RepoInsight",
  "environment": "production",
  "uptime_seconds": 5,
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}

[ ] Health check shows all services connected
[ ] Frontend accessible at http://localhost:80
[ ] API accessible at http://localhost:8000
[ ] No --reload in production logs
[ ] GitHub Actions workflow visible in repo Actions tab after push

---

## Project Complete

All 13 parts are done. Summary of what was built:

Backend Services:
- GitHub API integration (fetch repo data)
- Repository cloning + AST analysis
- Multi-model LLM (Gemini + Groq, 8 parallel calls)
- Quota monitor with dual-project fallback
- Opportunity scoring engine
- Developer-opportunity matching algorithm
- Celery async job pipeline
- PDF generation (3 report types)
- 10+ REST API endpoints

Frontend:
- Dark sidebar layout (GitHub-inspired)
- URL input with skill level selector
- Real-time progress polling
- Tabbed results dashboard
- Opportunity cards with difficulty badges
- Match percentage display
- PDF download buttons

Infrastructure:
- Docker + Docker Compose (dev + prod)
- PostgreSQL + Redis
- Celery worker
- Nginx reverse proxy
- GitHub Actions CI/CD
- Railway deployment config

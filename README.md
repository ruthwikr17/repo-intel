<div align="center">

# RepoIntel

### *AI-Powered Open-Source Repository Intelligence, AST Code Analysis & Contributor Matchmaker*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg?style=flat-square&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A.svg?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

---

**RepoIntel** transforms any open-source GitHub repository into an actionable developer onboarding experience. By combining static AST code analysis, GitHub REST/MCP integration, multi-model LLM reasoning (Gemini + Groq Llama), a contribution scoring algorithm, personalized developer skill matching, and vector-ready PDF report generation, RepoIntel helps developers start contributing to complex codebases within minutes.

[Features](#-key-features) • [Architecture](#-system-architecture) • [Tech Stack](#-tech-stack) • [Getting Started](#-getting-started) • [API Documentation](#-api-reference) • [Workflow](#-analysis-pipeline-a-to-z) • [Contributing](#-contributing)

</div>

---

## 🌟 Key Features

- 🔍 **Deep AST & Static Code Intelligence**: Analyzes file hierarchy, functions, classes, dependencies, cyclomatic complexity, code quality indicators, and architectural patterns.
- 🤖 **Tiered Multi-LLM Orchestration**:
  - **Tier 1 (High Quality Hybrid)**: Executes 9 concurrent async tasks leveraging Google Gemini 2.5 Flash for deep reasoning and Groq (`openai/gpt-oss-120b`) for structured generation.
  - **Tier 2 (Groq Fallback)**: Gracefully falls back to pure Groq inference when quotas are exceeded.
- 🎯 **Smart Contribution Scorer & Categorizer**: Generates and categorizes actionable tasks (Features, Docs, Testing, Tooling, Performance, Refactoring) with estimated difficulty, learning value, and realistic time metrics (30–120 mins).
- 🧩 **Developer Skill Matchmaker**: Matches issues and suggested tasks to developers based on experience level (Beginner, Intermediate, Advanced) and weekly available time budget.
- 📑 **Publication-Ready PDF Reports**: Instant one-click generation of 3 tailored reports using Jinja2 and WeasyPrint:
  - *Contributor Guide*
  - *Executive Summary*
  - *Code Quality Assessment*
- 🤖 **One-Click AI Helper Integration**: Export curated prompt context directly into **ChatGPT**, **Gemini**, or **Claude** with full repository state and issue context.
- 📊 **Real-time Analytics Dashboard**: Tracks overall repository insights, daily analysis trends, language breakdowns, and task distributions.
- 🌓 **Full Light & Dark Theme**: Built-in dynamic theme toggling with curated GitHub-inspired HSL CSS tokens.

---

## 🏗 System Architecture

```
                                  ┌──────────────────────────┐
                                  │      React + Vite UI     │
                                  │ (TailwindCSS, TypeScript)│
                                  └─────────────┬────────────┘
                                                │ REST API / JSON
                                                ▼
                                  ┌──────────────────────────┐
                                  │    FastAPI Application   │
                                  │ (Async Web/API Backend)  │
                                  └──────┬────────────┬──────┘
                                         │            │
             ┌───────────────────────────┘            └──────────────────────────┐
             ▼                                                                   ▼
┌──────────────────────────┐                                       ┌──────────────────────────┐
│   PostgreSQL Database    │                                       │   Redis Task Broker &    │
│  (SQLAlchemy + Asyncpg)  │                                       │      Cache Storage       │
└──────────────────────────┘                                       └────────────┬─────────────┘
                                                                                │
                                                                                ▼
                                                                   ┌──────────────────────────┐
                                                                   │   Celery Async Worker    │
                                                                   │ (Background Task Runner) │
                                                                   └────────────┬─────────────┘
                                                                                │
                     ┌──────────────────────────────────────────────────────────┴────────────────────────────────┐
                     ▼                                                          ▼                                ▼
       ┌──────────────────────────┐                               ┌──────────────────────────┐     ┌──────────────────────────┐
       │   GitHub REST & MCP API  │                               │    Hybrid LLM Services   │     │    WeasyPrint Engine     │
       │ (Metadata, Issues, Commits│                               │  (Gemini + Groq Llama)   │     │  (PDF Report Generation) │
       └──────────────────────────┘                               └──────────────────────────┘     └──────────────────────────┘
```

---

## 🛠 Tech Stack

### **Backend & Core Engine**
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11 asynchronous ASGI web framework)
- **Task Queue & Async Processing**: [Celery](https://docs.celeryq.dev/) with [Redis](https://redis.io/) broker
- **Database**: [PostgreSQL 15](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) async ORM and [asyncpg](https://github.com/MagicStack/asyncpg) driver
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **PDF Generation Engine**: [WeasyPrint](https://weasyprint.org/) + [Jinja2](https://jinja.palletsprojects.com/)
- **AI / LLM Providers**:
  - Google Generative AI (`gemini-2.5-flash`)
  - Groq Cloud API (`openai/gpt-oss-120b`)
  - Dual Gemini project API quota rotation
- **MCP Integration**: Model Context Protocol (MCP) Python SDK for GitHub API client

### **Frontend Client**
- **Framework**: [React 18](https://reactjs.org/) + [TypeScript](https://www.typescriptlang.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS 3.4](https://tailwindcss.com/) + Custom CSS variable design system
- **Markdown & Code Rendering**: `react-markdown`

### **DevOps & Containerization**
- **Containerization**: [Docker](https://www.docker.com/) & Docker Compose
- **Server**: Uvicorn ASGI Server

---

## 📂 Project Structure

```
.
├── backend/
│   ├── alembic/                  # Database migration schemas
│   ├── app/
│   │   ├── models/               # SQLAlchemy models (Repo, Analysis, Opportunity, etc.)
│   │   ├── routes/               # API Routers (repos, pdfs, analytics, health, admin)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── services/             # Core engines:
│   │   │   ├── github_service.py # GitHub REST & Tree extraction
│   │   │   ├── github_mcp_service.py # GitHub MCP Server client
│   │   │   ├── repo_analyzer.py  # AST Python & JavaScript code parser
│   │   │   ├── llm_service.py    # Multi-tier LLM parallel runner
│   │   │   ├── prompts.py        # System prompt templates
│   │   │   ├── quota_monitor.py  # Gemini & Groq quota load balancing
│   │   │   ├── scoring_engine.py # Opportunity ranking & heuristics
│   │   │   ├── matching_engine.py# User profile skill matchmaker
│   │   │   └── pdf_service.py    # WeasyPrint PDF renderer with Markdown filters
│   │   ├── tasks/
│   │   │   └── analysis_task.py  # Celery asynchronous analysis pipeline
│   │   ├── templates/            # HTML/CSS templates for PDF reports
│   │   ├── config.py             # App environment configuration (pydantic-settings)
│   │   ├── database.py           # Async engine and session factory
│   │   ├── main.py               # FastAPI entrypoint
│   │   └── worker.py             # Celery entrypoint
│   ├── tests/                    # Backend unit & integration tests
│   ├── Dockerfile                # Backend container definition
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variables template
│
├── frontend/
│   ├── src/
│   │   ├── api/                  # Axios/Fetch API client
│   │   ├── components/
│   │   │   ├── Analysis/         # Results dashboard, progress tracker, tabs
│   │   │   ├── Dashboard/        # Analytics, charts, activity feeds
│   │   │   ├── Home/             # Repo URL input, search history
│   │   │   ├── Layout/           # Sidebar, navbar, layout wrapper
│   │   │   ├── Opportunities/    # AI helper buttons, cards, list, filters
│   │   │   └── shared/           # Spinners, badges, error states
│   │   ├── hooks/                # Custom React hooks (useAnalysis)
│   │   ├── types/                # TypeScript type declarations
│   │   ├── App.tsx               # Main application container & routing
│   │   └── index.css             # Tailwind & Theme tokens
│   ├── package.json              # Frontend dependencies
│   └── vite.config.ts            # Vite proxy & server configuration
│
├── docker-compose.yml            # Multi-container orchestration
└── README.md                     # Documentation
```

---

## 🚀 Getting Started

### Prerequisites
Make sure you have the following installed:
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Node.js](https://nodejs.org/) (v18+ recommended) & `npm`
- [Python](https://www.python.org/) 3.11+ (if running without Docker)
- API Keys:
  - [GitHub Personal Access Token](https://github.com/settings/tokens) (classic or fine-grained with `repo` scope)
  - [Google Gemini API Key](https://aistudio.google.com/) (Optionally 2 keys for dual quota fallback)
  - [Groq Cloud API Key](https://console.groq.com/)

---

### Quick Start with Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ruthwikr17/repo-intel.git
   cd repo-intel
   ```

2. **Configure Environment Variables**:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Open `backend/.env` in your editor and add your API keys:
   ```ini
   APP_NAME=RepoInsight
   APP_ENV=development
   DEBUG=true

   DATABASE_URL=postgresql+asyncpg://repoinsight:repoinsight@db:5432/repoinsight
   REDIS_URL=redis://cache:6379/0

   GITHUB_TOKEN=ghp_your_personal_access_token
   GEMINI_API_KEY_PROJECT_A=your_gemini_api_key_1
   GEMINI_API_KEY_PROJECT_B=your_gemini_api_key_2
   GROQ_API_KEY=gsk_your_groq_api_key
   SECRET_KEY=supersecretkey_min_32_characters_long
   ```

3. **Start All Services with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```
   This will spin up:
   - `backend` (FastAPI at `http://localhost:8000`)
   - `worker` (Celery background worker)
   - `db` (PostgreSQL 15 at `localhost:5433`)
   - `cache` (Redis at `localhost:6379`)

4. **Start the Frontend Client**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser!

---

### Manual Local Setup (Without Docker)

<details>
<summary>Click to view manual setup instructions</summary>

#### 1. Start PostgreSQL & Redis
Ensure PostgreSQL is running on port `5432` with database `repoinsight`, and Redis is running on port `6379`.

#### 2. Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations/create tables
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start Celery Worker (In a separate terminal)
```bash
cd backend
source venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info
```

#### 4. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
</details>

---

## 🔄 Analysis Pipeline (A to Z)

```
[ User Submits GitHub URL ]
             │
             ▼
[ POST /api/repos/analyze ] ──► [ Celery Task Enqueued ] ──► [ Returns task_id ]
                                            │
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │           1. GitHub Extraction           │
                       │ Fetches Repo info, README, Issues, Tree, │
                       │ Commits, Releases, Contributors          │
                       └────────────────────┬─────────────────────┘
                                            │
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │           2. AST Code Analysis           │
                       │ Parses Python AST & JS/TS files, builds  │
                       │ file metrics, cyclomatic complexity,     │
                       │ imports, functions & error antipatterns  │
                       └────────────────────┬─────────────────────┘
                                            │
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │          3. 9-Way LLM Generation        │
                       │ Summary, Architecture, Code Walkthrough, │
                       │ Quality Report, Setup Guide, Gotchas,    │
                       │ Common Patterns, Suggestions, Narrative │
                       └────────────────────┬─────────────────────┘
                                            │
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │        4. Scoring & Matchmaking          │
                       │ Ranks tasks into Beginner/Intermediate/  │
                       │ Advanced tiers with time & impact scores │
                       └────────────────────┬─────────────────────┘
                                            │
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │        5. Persistence & Delivery         │
                       │ Upserts PostgreSQL analysis record &     │
                       │ broadcasts completion status to frontend │
                       └──────────────────────────────────────────┘
```

---

## 📖 API Reference

Explore the interactive Swagger UI documentation at: **`http://localhost:8000/docs`**

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Healthcheck (API, Database connection) |
| `POST` | `/api/repos/analyze` | Initiates asynchronous repository analysis job |
| `GET` | `/api/repos/tasks/{task_id}` | Polls status of a running analysis task |
| `GET` | `/api/repos/{repo_id}/analysis` | Returns latest complete analysis for a repository |
| `GET` | `/api/repos/{repo_id}/opportunities` | Retrieves scored contribution opportunities |
| `POST` | `/api/repos/{repo_id}/matched` | Returns personalized matches based on user skill profile |
| `GET` | `/api/repos/{repo_id}/opportunities/{opp_id}/ai-context` | Generates formatted prompt context for ChatGPT/Claude/Gemini |
| `POST` | `/api/pdfs/generate` | Generates PDF report (`contributor_guide`, `executive_summary`, `code_quality`) |
| `GET` | `/api/pdfs/download/{filename}` | Downloads generated PDF binary |
| `GET` | `/api/analytics/overview` | Retrieves system-wide platform statistics & activity metrics |
| `GET` | `/api/repos/recent` | Lists recently analyzed repositories |

---

## 🧪 Running Tests

The test suite covers API routes, model validations, scoring algorithms, matching engine heuristics, and quota management:

```bash
# Run backend tests
cd backend
pytest -v
```

---

## 📊 Analytics & Reporting

RepoIntel includes an analytics suite designed to monitor platform metrics:
- **Repository Language Distribution**: Breakdown of repositories analyzed by primary programming language.
- **Contribution Opportunities by Category**: Distribution across Documentation, Features, Testing, Performance, and Tooling.
- **Quality Tier Tracking**: Tracks high-tier vs fallback-tier LLM generation results.
- **Activity Feed**: Real-time log of analyzed repositories and generated insights.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  Built with ❤️ for Open-Source Contributors and Maintainers worldwide.
</div>

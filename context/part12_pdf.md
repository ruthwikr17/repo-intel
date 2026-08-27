# CONTEXT FILE: Part 12 - PDF Generation
# Project: RepoInsight
# Read the existing codebase before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-11

- Full backend pipeline (Parts 1-10)
- React frontend with results dashboard (Part 11)
- Models: RepositoryAnalysis, Repository, PdfReport

---

## What Part 12 Builds

- PDF generation service using Weasyprint
- HTML templates for 3 PDF types (Contributor Guide, Executive Summary, Code Quality)
- POST /api/pdfs/generate endpoint
- GET /api/pdfs/download/{pdf_id} endpoint
- Download button added to frontend ResultsDashboard

New packages - add to backend/requirements.txt:
- weasyprint==62.3
- jinja2==3.1.4

---

## Files to Create or Modify

- backend/app/services/pdf_service.py       (NEW)
- backend/app/templates/contributor_guide.html  (NEW)
- backend/app/templates/executive_summary.html  (NEW)
- backend/app/templates/code_quality.html       (NEW)
- backend/app/routes/pdfs.py                (NEW)
- backend/app/main.py                       (MODIFY - add pdf router)
- frontend/src/components/Analysis/ResultsDashboard.tsx  (MODIFY - add download button)

---

## PDF Service

### backend/app/services/pdf_service.py

```python
import os
import uuid
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path("/tmp/repoinsight_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)


def get_jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def generate_contributor_guide(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    """
    Generate Contributor Guide PDF.
    Returns file path of generated PDF.
    """
    env = get_jinja_env()
    template = env.get_template("contributor_guide.html")

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
        beginner_opps=[o for o in opportunities if o.get("difficulty_tier") == "beginner"],
        intermediate_opps=[o for o in opportunities if o.get("difficulty_tier") == "intermediate"],
        advanced_opps=[o for o in opportunities if o.get("difficulty_tier") == "advanced"],
    )

    filename = f"contributor_guide_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    HTML(string=html_content).write_pdf(str(output_path))
    return str(output_path)


def generate_executive_summary(
    analysis: dict,
    repo: dict,
) -> str:
    """Generate Executive Summary PDF. Returns file path."""
    env = get_jinja_env()
    template = env.get_template("executive_summary.html")

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )

    filename = f"executive_summary_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    HTML(string=html_content).write_pdf(str(output_path))
    return str(output_path)


def generate_code_quality_report(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    """Generate Code Quality Analysis PDF. Returns file path."""
    env = get_jinja_env()
    template = env.get_template("code_quality.html")

    metrics = analysis.get("code_quality_metrics", {}) or {}

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        metrics=metrics,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )

    filename = f"code_quality_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    HTML(string=html_content).write_pdf(str(output_path))
    return str(output_path)
```

---

## HTML Templates

### backend/app/templates/contributor_guide.html

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         color: #24292f; font-size: 13px; line-height: 1.6; }
  .page { padding: 40px 50px; }
  .cover { background: #0d1117; color: white; padding: 60px 50px;
           min-height: 200px; }
  .cover h1 { font-size: 28px; margin-bottom: 8px; }
  .cover .accent { color: #2ea44f; }
  .cover p { color: #8b949e; font-size: 13px; margin-top: 6px; }
  h2 { font-size: 16px; color: #24292f; margin: 24px 0 12px;
       padding-bottom: 6px; border-bottom: 1px solid #e1e4e8; }
  h3 { font-size: 13px; font-weight: 600; color: #24292f; margin: 16px 0 8px; }
  p { margin-bottom: 10px; color: #24292f; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
           font-size: 11px; font-weight: 500; margin: 2px; }
  .badge-beginner { background: #dafbe1; color: #2ea44f; border: 1px solid #9be9a8; }
  .badge-intermediate { background: #fff3e0; color: #fb8500; border: 1px solid #ffcc80; }
  .badge-advanced { background: #ffeef0; color: #e03e2d; border: 1px solid #ffc1c0; }
  .badge-high { background: #dafbe1; color: #2ea44f; }
  .badge-medium { background: #fff3e0; color: #fb8500; }
  .stat-row { display: flex; gap: 24px; margin: 12px 0; }
  .stat { text-align: center; }
  .stat .number { font-size: 22px; font-weight: 700; color: #24292f; }
  .stat .label { font-size: 11px; color: #57606a; }
  .opp-card { border: 1px solid #e1e4e8; border-radius: 6px; padding: 12px;
              margin-bottom: 8px; }
  .opp-title { font-weight: 600; margin-bottom: 4px; }
  .opp-meta { font-size: 11px; color: #57606a; }
  .section { margin-bottom: 24px; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px;
         font-family: monospace; font-size: 12px; }
  pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px;
        padding: 12px; font-family: monospace; font-size: 11px;
        white-space: pre-wrap; margin: 8px 0; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e1e4e8;
            font-size: 11px; color: #57606a; text-align: center; }
</style>
</head>
<body>

<!-- Cover -->
<div class="cover">
  <h1>Repo<span class="accent">Insight</span></h1>
  <h2 style="color:white; border:none; margin-top:16px; font-size:20px;">
    Contributor Guide
  </h2>
  <p>{{ repo.full_name }}</p>
  <p>Generated {{ generated_at }}</p>
</div>

<div class="page">

  <!-- Repo Stats -->
  <div class="section">
    <h2>Repository Overview</h2>
    <p>{{ analysis.summary }}</p>
    <div class="stat-row">
      <div class="stat">
        <div class="number">{{ repo.stars }}</div>
        <div class="label">Stars</div>
      </div>
      <div class="stat">
        <div class="number">{{ repo.forks }}</div>
        <div class="label">Forks</div>
      </div>
      <div class="stat">
        <div class="number">{{ repo.open_issues_count }}</div>
        <div class="label">Open Issues</div>
      </div>
    </div>
    <p><strong>Language:</strong> {{ repo.language }}
       &nbsp;&nbsp;<strong>License:</strong> {{ repo.license or 'Unknown' }}</p>
  </div>

  <!-- Architecture -->
  <div class="section">
    <h2>Architecture</h2>
    <p>{{ analysis.architecture_explanation }}</p>
  </div>

  <!-- Setup Guide -->
  <div class="section">
    <h2>Setup Guide</h2>
    <pre>{{ analysis.setup_guide }}</pre>
  </div>

  <!-- Gotchas -->
  {% if analysis.gotchas_and_tips %}
  <div class="section">
    <h2>Gotchas & Tips</h2>
    <p>{{ analysis.gotchas_and_tips }}</p>
  </div>
  {% endif %}

  <!-- Opportunities -->
  <div class="section">
    <h2>Contribution Opportunities ({{ opportunities|length }} total)</h2>

    {% if beginner_opps %}
    <h3>Beginner <span class="badge badge-beginner">{{ beginner_opps|length }}</span></h3>
    {% for opp in beginner_opps[:5] %}
    <div class="opp-card">
      <div class="opp-title">{{ opp.title }}</div>
      <div class="opp-meta">
        ⏱ {{ opp.estimated_hours }}h &nbsp;
        📚 Learning: {{ opp.learning_value }}/10 &nbsp;
        💥 Impact: {{ opp.impact }}/10
        {% if opp.github_issue_url %}
        &nbsp; <a href="{{ opp.github_issue_url }}">#{{ opp.github_issue_number }}</a>
        {% endif %}
      </div>
    </div>
    {% endfor %}
    {% endif %}

    {% if intermediate_opps %}
    <h3>Intermediate <span class="badge badge-intermediate">{{ intermediate_opps|length }}</span></h3>
    {% for opp in intermediate_opps[:5] %}
    <div class="opp-card">
      <div class="opp-title">{{ opp.title }}</div>
      <div class="opp-meta">
        ⏱ {{ opp.estimated_hours }}h &nbsp;
        📚 Learning: {{ opp.learning_value }}/10 &nbsp;
        💥 Impact: {{ opp.impact }}/10
      </div>
    </div>
    {% endfor %}
    {% endif %}

  </div>

  <div class="footer">
    Generated by RepoInsight &bull; repoinsight.dev
  </div>
</div>
</body>
</html>
```

---

### backend/app/templates/executive_summary.html

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         color: #24292f; font-size: 13px; }
  .page { padding: 50px; }
  .header { border-bottom: 3px solid #2ea44f; padding-bottom: 16px; margin-bottom: 24px; }
  .header h1 { font-size: 22px; }
  .header p { color: #57606a; font-size: 12px; margin-top: 4px; }
  .score-box { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px;
               padding: 20px; margin: 20px 0; text-align: center; }
  .score-box .tier { font-size: 28px; font-weight: 700; color: #2ea44f; }
  .score-box p { color: #57606a; font-size: 12px; margin-top: 4px; }
  h2 { font-size: 14px; font-weight: 600; margin: 20px 0 8px;
       color: #24292f; border-left: 3px solid #2ea44f; padding-left: 8px; }
  p { color: #24292f; line-height: 1.6; margin-bottom: 8px; }
  .stats { display: flex; gap: 16px; margin: 16px 0; }
  .stat { flex: 1; text-align: center; border: 1px solid #e1e4e8;
          border-radius: 6px; padding: 12px; }
  .stat .n { font-size: 20px; font-weight: 700; }
  .stat .l { font-size: 11px; color: #57606a; }
  .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #57606a; }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>Executive Summary — {{ repo.full_name }}</h1>
    <p>Generated by RepoInsight &bull; {{ generated_at }}</p>
  </div>

  <div class="score-box">
    <div class="tier">{{ analysis.quality_tier }} Quality</div>
    <p>{{ repo.language }} &bull; {{ repo.stars }} stars &bull; {{ repo.license or 'Unknown license' }}</p>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="n">{{ repo.stars }}</div>
      <div class="l">Stars</div>
    </div>
    <div class="stat">
      <div class="n">{{ repo.forks }}</div>
      <div class="l">Forks</div>
    </div>
    <div class="stat">
      <div class="n">{{ repo.open_issues_count }}</div>
      <div class="l">Open Issues</div>
    </div>
  </div>

  <h2>Summary</h2>
  <p>{{ analysis.summary }}</p>

  <h2>Executive Assessment</h2>
  <p>{{ analysis.executive_summary or 'See full analysis for details.' }}</p>

  <div class="footer">Generated by RepoInsight</div>
</div>
</body>
</html>
```

---

### backend/app/templates/code_quality.html

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         color: #24292f; font-size: 13px; }
  .page { padding: 40px 50px; }
  .cover { background: #0d1117; color: white; padding: 40px 50px; }
  .cover h1 { font-size: 22px; color: #2ea44f; }
  .cover p { color: #8b949e; font-size: 12px; margin-top: 8px; }
  h2 { font-size: 15px; color: #24292f; margin: 20px 0 10px;
       padding-bottom: 6px; border-bottom: 1px solid #e1e4e8; }
  p { line-height: 1.6; margin-bottom: 10px; }
  .metric-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
  .metric { border: 1px solid #e1e4e8; border-radius: 6px; padding: 12px;
            min-width: 120px; text-align: center; }
  .metric .val { font-size: 20px; font-weight: 700; color: #24292f; }
  .metric .lbl { font-size: 11px; color: #57606a; margin-top: 2px; }
  .issue-row { border-bottom: 1px solid #f0f0f0; padding: 8px 0; font-size: 12px; }
  .issue-file { color: #57606a; font-family: monospace; font-size: 11px; }
  .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #57606a; }
</style>
</head>
<body>

<div class="cover">
  <h1>Code Quality Report</h1>
  <p>{{ repo.full_name }}</p>
  <p>{{ generated_at }}</p>
</div>

<div class="page">
  <h2>Metrics Overview</h2>
  <div class="metric-grid">
    <div class="metric">
      <div class="val">{{ metrics.files_analyzed or 0 }}</div>
      <div class="lbl">Files Analyzed</div>
    </div>
    <div class="metric">
      <div class="val">{{ metrics.total_functions or 0 }}</div>
      <div class="lbl">Functions</div>
    </div>
    <div class="metric">
      <div class="val">{{ metrics.total_classes or 0 }}</div>
      <div class="lbl">Classes</div>
    </div>
    <div class="metric">
      <div class="val">{{ "%.1f"|format(metrics.avg_complexity or 0) }}</div>
      <div class="lbl">Avg Complexity</div>
    </div>
    <div class="metric">
      <div class="val">{{ (metrics.all_issues or [])|length }}</div>
      <div class="lbl">Issues Found</div>
    </div>
  </div>

  <h2>Architecture Assessment</h2>
  <p>{{ analysis.architecture_explanation }}</p>

  <h2>Common Patterns</h2>
  <p>{{ analysis.common_patterns }}</p>

  {% if metrics.all_issues %}
  <h2>Detected Issues ({{ (metrics.all_issues or [])|length }})</h2>
  {% for issue in (metrics.all_issues or [])[:20] %}
  <div class="issue-row">
    <span>{{ issue.issue }}</span>
    <br><span class="issue-file">{{ issue.file }}</span>
  </div>
  {% endfor %}
  {% endif %}

  <h2>Contribution Opportunities</h2>
  {% for opp in opportunities[:10] %}
  <div class="issue-row">
    <strong>{{ opp.title }}</strong> —
    {{ opp.difficulty_tier }} &bull;
    {{ opp.estimated_hours }}h estimate
  </div>
  {% endfor %}

  <div class="footer">Generated by RepoInsight</div>
</div>
</body>
</html>
```

---

## PDF Route

### backend/app/routes/pdfs.py

```python
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.models.pdf_report import PdfReport
from app.services.pdf_service import (
    generate_contributor_guide,
    generate_executive_summary,
    generate_code_quality_report,
)

router = APIRouter()


class PdfRequest(BaseModel):
    repo_id: int
    report_type: str  # contributor_guide / executive_summary / code_quality


@router.post("/pdfs/generate")
async def generate_pdf(request: PdfRequest, db: AsyncSession = Depends(get_db)):
    """Generate a PDF report for a repository."""

    # Get repo
    repo_result = await db.execute(
        select(Repository).where(Repository.id == request.repo_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get analysis
    analysis_result = await db.execute(
        select(RepositoryAnalysis).where(
            RepositoryAnalysis.repo_id == request.repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")

    # Get opportunities
    opps_result = await db.execute(
        select(Opportunity)
        .where(Opportunity.repo_id == request.repo_id)
        .order_by(Opportunity.overall_score.desc())
    )
    opportunities = opps_result.scalars().all()

    # Build dicts for templates
    repo_dict = {
        "full_name": repo.full_name,
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "forks": repo.forks,
        "open_issues_count": repo.open_issues_count,
        "license": repo.license,
    }

    analysis_dict = {
        "summary": analysis.summary,
        "architecture_explanation": analysis.architecture_explanation,
        "code_walkthrough": analysis.code_walkthrough,
        "common_patterns": analysis.common_patterns,
        "gotchas_and_tips": analysis.gotchas_and_tips,
        "setup_guide": analysis.setup_guide,
        "quality_tier": analysis.quality_tier,
        "executive_summary": None,
        "code_quality_metrics": analysis.code_quality_metrics,
    }

    opp_list = [
        {
            "title": o.title,
            "description": o.description,
            "category": o.category,
            "difficulty": o.difficulty,
            "impact": o.impact,
            "learning_value": o.learning_value,
            "overall_score": o.overall_score,
            "estimated_hours": o.estimated_hours,
            "difficulty_tier": o.difficulty_tier,
            "github_issue_number": o.github_issue_number,
            "github_issue_url": o.github_issue_url,
        }
        for o in opportunities
    ]

    # Generate PDF
    try:
        if request.report_type == "contributor_guide":
            file_path = generate_contributor_guide(analysis_dict, repo_dict, opp_list)
        elif request.report_type == "executive_summary":
            file_path = generate_executive_summary(analysis_dict, repo_dict)
        elif request.report_type == "code_quality":
            file_path = generate_code_quality_report(analysis_dict, repo_dict, opp_list)
        else:
            raise HTTPException(status_code=400, detail="Invalid report_type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    # Save record
    pdf_record = PdfReport(
        repo_id=repo.id,
        analysis_id=analysis.id,
        report_type=request.report_type,
        file_path=file_path,
        file_size_bytes=os.path.getsize(file_path),
    )
    db.add(pdf_record)
    await db.commit()
    await db.refresh(pdf_record)

    return {
        "pdf_id": pdf_record.id,
        "report_type": request.report_type,
        "file_size_bytes": pdf_record.file_size_bytes,
        "download_url": f"/api/pdfs/download/{pdf_record.id}",
    }


@router.get("/pdfs/download/{pdf_id}")
async def download_pdf(pdf_id: int, db: AsyncSession = Depends(get_db)):
    """Download a generated PDF by ID."""
    result = await db.execute(
        select(PdfReport).where(PdfReport.id == pdf_id)
    )
    pdf_record = result.scalar_one_or_none()
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")

    if not os.path.exists(pdf_record.file_path):
        raise HTTPException(status_code=404, detail="PDF file missing from disk")

    filename = f"repoinsight_{pdf_record.report_type}_{pdf_record.repo_id}.pdf"
    return FileResponse(
        pdf_record.file_path,
        media_type="application/pdf",
        filename=filename,
    )
```

---

## Modify main.py

Add pdf router:

```python
from app.routes.pdfs import router as pdfs_router
app.include_router(pdfs_router, prefix="/api", tags=["pdfs"])
```

---

## Frontend: Add Download Button

### Modify frontend/src/components/Analysis/ResultsDashboard.tsx

Add this import at the top:
```typescript
import { useState as useDownloadState } from 'react';
```

Add this function inside ResultsDashboard component, before the return:
```typescript
const [downloading, setDownloading] = useState(false);

const handleDownloadPdf = async (reportType: string) => {
  setDownloading(true);
  try {
    const res = await fetch('/api/pdfs/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId, report_type: reportType }),
    });
    const data = await res.json();
    if (data.download_url) {
      window.open(data.download_url, '_blank');
    }
  } catch (e) {
    console.error('PDF download failed', e);
  } finally {
    setDownloading(false);
  }
};
```

Add this download bar just above the Tabs section in the JSX:
```tsx
{/* Download bar */}
<div className="flex gap-2 mb-4">
  <span className="text-sm mr-2" style={{ color: '#57606a' }}>
    Download PDF:
  </span>
  {[
    { label: 'Contributor Guide', type: 'contributor_guide' },
    { label: 'Executive Summary', type: 'executive_summary' },
    { label: 'Code Quality', type: 'code_quality' },
  ].map(({ label, type }) => (
    <button
      key={type}
      onClick={() => handleDownloadPdf(type)}
      disabled={downloading}
      className="text-xs px-3 py-1 rounded border"
      style={{
        borderColor: '#d0d7de',
        color: '#57606a',
        opacity: downloading ? 0.6 : 1,
      }}
    >
      {label}
    </button>
  ))}
</div>
```

---

## Validation Checklist

[ ] weasyprint and jinja2 added to requirements.txt
[ ] backend/app/services/pdf_service.py created
[ ] backend/app/templates/ folder created
[ ] All 3 HTML templates created
[ ] backend/app/routes/pdfs.py created
[ ] backend/app/main.py includes pdfs_router
[ ] Frontend ResultsDashboard has download buttons
[ ] Docker rebuilt: docker-compose down && docker-compose up --build -d

Manual tests:

1. Generate contributor guide:
curl -X POST http://localhost:8000/api/pdfs/generate \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "report_type": "contributor_guide"}'

Expected: {"pdf_id": 1, "download_url": "/api/pdfs/download/1", ...}

2. Download PDF:
curl http://localhost:8000/api/pdfs/download/1 --output test.pdf
open test.pdf

[ ] PDF opens and is readable
[ ] Contains repo name, opportunities, setup guide
[ ] Frontend download buttons trigger PDF generation and open in new tab

---

## What Part 13 Will Cover

Docker production setup and deployment to Railway.
Environment configuration, health checks, CI/CD with GitHub Actions.

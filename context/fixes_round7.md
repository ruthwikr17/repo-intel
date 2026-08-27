# CONTEXT FILE: Fix Round 7 - DB Migration + PDF Quality Overhaul
# Project: RepoInsight
# Two fixes: add missing DB column, completely redo PDF templates

---

## Fix 1: Add Missing Database Column (CRITICAL - Do This First)

The model has ai_suggestions but the table doesn't. Run this SQL migration.

### Option A: Run directly in PostgreSQL (fastest)

```bash
docker-compose exec db psql -U repoinsight -d repoinsight -c \
  "ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS ai_suggestions JSONB;"
```

### Option B: Add Alembic migration file

Create file: backend/alembic/versions/001_add_ai_suggestions.py

```python
"""add ai_suggestions column

Revision ID: 001
Revises: 
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'repository_analyses',
        sa.Column('ai_suggestions', postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('repository_analyses', 'ai_suggestions')
```

Then run:
```bash
docker-compose exec backend alembic upgrade head
```

Use Option A (fastest). Verify with:
```bash
docker-compose exec db psql -U repoinsight -d repoinsight -c \
  "\d repository_analyses" | grep ai_suggestions
```

Should show: ai_suggestions | jsonb

---

## Fix 2: PDF Templates Complete Rewrite

Current PDF problems seen in the uploaded files:
- Raw markdown (##, **, *) showing as plain text
- Repeated sections (Common Patterns appearing in both sections)
- No visual hierarchy
- Contributor guide has architecture showing raw ## headers
- Code quality report has architecture repeated verbatim
- No proper spacing between sections
- Monospace font used throughout (should only be for code)
- Poor typography

Replace ALL three templates:

### backend/app/templates/contributor_guide.html (REPLACE ENTIRELY)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: #24292f;
    font-size: 13px;
    line-height: 1.6;
  }

  .cover {
    background: #0d1117;
    color: white;
    padding: 60px 50px 50px;
    min-height: 220px;
  }

  .cover-logo {
    font-size: 13px;
    color: #2ea44f;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 24px;
  }

  .cover h1 {
    font-size: 26px;
    font-weight: 700;
    color: white;
    margin-bottom: 8px;
  }

  .cover .repo-name {
    font-size: 14px;
    color: #8b949e;
    font-family: monospace;
  }

  .cover .generated {
    font-size: 11px;
    color: #57606a;
    margin-top: 12px;
  }

  .page {
    padding: 40px 50px;
  }

  .stat-bar {
    display: flex;
    gap: 0;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    overflow: hidden;
    margin: 20px 0;
  }

  .stat-item {
    flex: 1;
    text-align: center;
    padding: 14px 10px;
    border-right: 1px solid #e1e4e8;
  }

  .stat-item:last-child { border-right: none; }

  .stat-item .stat-num {
    font-size: 22px;
    font-weight: 700;
    color: #24292f;
    display: block;
  }

  .stat-item .stat-label {
    font-size: 10px;
    color: #57606a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: block;
    margin-top: 2px;
  }

  h2 {
    font-size: 15px;
    font-weight: 600;
    color: #24292f;
    margin: 28px 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #2ea44f;
  }

  h3 {
    font-size: 13px;
    font-weight: 600;
    color: #24292f;
    margin: 16px 0 6px;
  }

  p {
    color: #24292f;
    margin-bottom: 10px;
    line-height: 1.7;
  }

  ul {
    padding-left: 18px;
    margin-bottom: 12px;
  }

  li {
    color: #24292f;
    margin-bottom: 4px;
    line-height: 1.6;
  }

  strong { font-weight: 600; color: #24292f; }

  code {
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 4px;
    padding: 1px 5px;
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 11px;
    color: #24292f;
  }

  pre {
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 14px 16px;
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 11px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 10px 0;
    color: #24292f;
  }

  .section-content {
    color: #24292f;
    line-height: 1.7;
  }

  .opp-tier-header {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 20px 0 10px;
    padding: 6px 10px;
    border-radius: 4px;
  }

  .tier-beginner { background: #dafbe1; color: #2ea44f; }
  .tier-intermediate { background: #fff3e0; color: #fb8500; }
  .tier-advanced { background: #ffeef0; color: #e03e2d; }

  .opp-card {
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }

  .opp-title {
    font-weight: 600;
    font-size: 13px;
    color: #24292f;
    margin-bottom: 4px;
  }

  .opp-desc {
    font-size: 12px;
    color: #57606a;
    margin-bottom: 6px;
    line-height: 1.5;
  }

  .opp-meta {
    font-size: 11px;
    color: #8b949e;
    display: flex;
    gap: 16px;
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .badge-beginner { background: #dafbe1; color: #2ea44f; }
  .badge-intermediate { background: #fff3e0; color: #fb8500; }
  .badge-advanced { background: #ffeef0; color: #e03e2d; }
  .badge-high { background: #dafbe1; color: #2ea44f; }
  .badge-medium { background: #fff3e0; color: #fb8500; }

  .info-row {
    display: flex;
    gap: 20px;
    margin: 12px 0;
    flex-wrap: wrap;
  }

  .info-tag {
    font-size: 12px;
    color: #57606a;
  }

  .info-tag strong {
    color: #24292f;
  }

  .footer {
    margin-top: 50px;
    padding-top: 14px;
    border-top: 1px solid #e1e4e8;
    font-size: 10px;
    color: #8b949e;
    text-align: center;
  }

  .page-break { page-break-before: always; }
</style>
</head>
<body>

<!-- COVER -->
<div class="cover">
  <div class="cover-logo">RepoInsight</div>
  <h1>Contributor Guide</h1>
  <div class="repo-name">{{ repo.full_name }}</div>
  <div class="generated">Generated {{ generated_at }}</div>
</div>

<!-- PAGE 1: Overview -->
<div class="page">

  <h2>Repository Overview</h2>

  <div class="stat-bar">
    <div class="stat-item">
      <span class="stat-num">{{ repo.stars }}</span>
      <span class="stat-label">Stars</span>
    </div>
    <div class="stat-item">
      <span class="stat-num">{{ repo.forks }}</span>
      <span class="stat-label">Forks</span>
    </div>
    <div class="stat-item">
      <span class="stat-num">{{ repo.open_issues_count }}</span>
      <span class="stat-label">Open Issues</span>
    </div>
    <div class="stat-item">
      <span class="stat-num">{{ opportunities | length }}</span>
      <span class="stat-label">Opportunities</span>
    </div>
  </div>

  <div class="info-row">
    <span class="info-tag"><strong>Language:</strong> {{ repo.language or 'Unknown' }}</span>
    <span class="info-tag"><strong>License:</strong> {{ repo.license or 'Unknown' }}</span>
    <span class="info-tag">
      <strong>Quality:</strong>
      <span class="badge {{ 'badge-high' if analysis.quality_tier == 'HIGH' else 'badge-medium' }}">
        {{ analysis.quality_tier }} Analysis
      </span>
    </span>
  </div>

  <!-- Summary: strip markdown symbols and render as clean paragraphs -->
  <div class="section-content">
    {% set summary_text = analysis.summary or '' %}
    {% for line in summary_text.split('\n') %}
      {% set stripped = line.strip() %}
      {% if stripped.startswith('## ') %}
        <h3>{{ stripped[3:] }}</h3>
      {% elif stripped.startswith('# ') %}
        <h3>{{ stripped[2:] }}</h3>
      {% elif stripped.startswith('**') and stripped.endswith('**') %}
        <h3>{{ stripped[2:-2] }}</h3>
      {% elif stripped %}
        <p>{{ stripped | replace('**', '') }}</p>
      {% endif %}
    {% endfor %}
  </div>

  <!-- Architecture -->
  <h2>Architecture</h2>
  <div class="section-content">
    {% set arch_text = analysis.architecture_explanation or '' %}
    {% for line in arch_text.split('\n') %}
      {% set stripped = line.strip() %}
      {% if stripped.startswith('## ') %}
        <h3>{{ stripped[3:] }}</h3>
      {% elif stripped.startswith('- ') or stripped.startswith('* ') %}
        <p style="padding-left:12px; color:#57606a;">• {{ stripped[2:] | replace('**','') }}</p>
      {% elif stripped %}
        <p>{{ stripped | replace('**', '') | replace('*', '') }}</p>
      {% endif %}
    {% endfor %}
  </div>

  <!-- Setup Guide -->
  <h2>Setup Guide</h2>
  <div class="section-content">
    {% set setup_text = analysis.setup_guide or '' %}
    {% for line in setup_text.split('\n') %}
      {% set stripped = line.strip() %}
      {% if stripped.startswith('## ') %}
        <h3>{{ stripped[3:] }}</h3>
      {% elif stripped.startswith('```') %}
        {# skip code fence markers #}
      {% elif stripped.startswith('`') and stripped.endswith('`') %}
        <pre>{{ stripped[1:-1] }}</pre>
      {% elif stripped.startswith('- ') or stripped.startswith('* ') %}
        <p style="padding-left:12px; color:#57606a;">• {{ stripped[2:] }}</p>
      {% elif stripped[0:2].isdigit() and '.' in stripped %}
        <p><strong>{{ stripped }}</strong></p>
      {% elif stripped %}
        <p>{{ stripped }}</p>
      {% endif %}
    {% endfor %}
  </div>

  <!-- Gotchas -->
  {% if analysis.gotchas_and_tips %}
  <h2>Gotchas & Tips</h2>
  <div class="section-content">
    {% for line in analysis.gotchas_and_tips.split('\n') %}
      {% set stripped = line.strip() %}
      {% if stripped.startswith('## ') %}
        <h3>{{ stripped[3:] }}</h3>
      {% elif stripped.startswith('**') %}
        <h3>{{ stripped | replace('**', '') | replace(':', '') }}</h3>
      {% elif stripped.startswith('- ') or stripped.startswith('* ') %}
        <p style="padding-left:12px; color:#57606a;">• {{ stripped[2:] | replace('**','') }}</p>
      {% elif stripped %}
        <p>{{ stripped | replace('**', '') }}</p>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  <!-- Contribution Opportunities -->
  <h2>Contribution Opportunities</h2>
  <p style="color:#57606a; font-size:12px; margin-bottom:16px;">
    {{ opportunities | length }} total opportunities across {{ beginner_opps | length }} beginner,
    {{ intermediate_opps | length }} intermediate, and {{ advanced_opps | length }} advanced tasks.
  </p>

  {% if beginner_opps %}
  <div class="opp-tier-header tier-beginner">Beginner — 1-3 hours</div>
  {% for opp in beginner_opps[:6] %}
  <div class="opp-card">
    <div class="opp-title">{{ opp.title }}</div>
    {% if opp.description %}
    <div class="opp-desc">{{ opp.description[:200] }}{% if opp.description | length > 200 %}...{% endif %}</div>
    {% endif %}
    <div class="opp-meta">
      <span>⏱ {{ opp.estimated_hours }}h estimate</span>
      <span>📚 Learning: {{ opp.learning_value }}/10</span>
      <span>💥 Impact: {{ opp.impact }}/10</span>
      {% if opp.github_issue_url %}
      <span>🔗 Issue #{{ opp.github_issue_number }}</span>
      {% endif %}
    </div>
  </div>
  {% endfor %}
  {% endif %}

  {% if intermediate_opps %}
  <div class="opp-tier-header tier-intermediate">Intermediate — 4-8 hours</div>
  {% for opp in intermediate_opps[:6] %}
  <div class="opp-card">
    <div class="opp-title">{{ opp.title }}</div>
    {% if opp.description %}
    <div class="opp-desc">{{ opp.description[:200] }}{% if opp.description | length > 200 %}...{% endif %}</div>
    {% endif %}
    <div class="opp-meta">
      <span>⏱ {{ opp.estimated_hours }}h estimate</span>
      <span>📚 Learning: {{ opp.learning_value }}/10</span>
      <span>💥 Impact: {{ opp.impact }}/10</span>
    </div>
  </div>
  {% endfor %}
  {% endif %}

  {% if advanced_opps %}
  <div class="opp-tier-header tier-advanced">Advanced — 8+ hours</div>
  {% for opp in advanced_opps[:4] %}
  <div class="opp-card">
    <div class="opp-title">{{ opp.title }}</div>
    {% if opp.description %}
    <div class="opp-desc">{{ opp.description[:200] }}{% if opp.description | length > 200 %}...{% endif %}</div>
    {% endif %}
    <div class="opp-meta">
      <span>⏱ {{ opp.estimated_hours }}h estimate</span>
      <span>📚 Learning: {{ opp.learning_value }}/10</span>
      <span>💥 Impact: {{ opp.impact }}/10</span>
    </div>
  </div>
  {% endfor %}
  {% endif %}

  <div class="footer">
    Generated by RepoInsight &bull; repoinsight.dev &bull; {{ generated_at }}
  </div>
</div>

</body>
</html>
```

---

### backend/app/templates/executive_summary.html (REPLACE ENTIRELY)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: #24292f;
    font-size: 13px;
  }
  .page { padding: 50px; }
  .header {
    border-bottom: 3px solid #2ea44f;
    padding-bottom: 16px;
    margin-bottom: 28px;
  }
  .header .logo { font-size: 11px; color: #2ea44f; letter-spacing: 2px;
                  text-transform: uppercase; margin-bottom: 8px; }
  .header h1 { font-size: 20px; font-weight: 700; color: #24292f; }
  .header .sub { font-size: 12px; color: #57606a; margin-top: 4px;
                 font-family: monospace; }
  .header .date { font-size: 11px; color: #8b949e; margin-top: 4px; }

  .quality-banner {
    text-align: center;
    padding: 24px;
    border-radius: 8px;
    margin: 20px 0;
    border: 2px solid #2ea44f;
    background: #f0fff4;
  }
  .quality-banner .tier-label { font-size: 28px; font-weight: 800;
                                 color: #2ea44f; display: block; }
  .quality-banner .tier-sub { font-size: 12px; color: #57606a; margin-top: 4px; }

  .stat-row {
    display: flex;
    gap: 12px;
    margin: 20px 0;
  }
  .stat-box {
    flex: 1;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 14px;
    text-align: center;
  }
  .stat-box .num { font-size: 24px; font-weight: 700; color: #24292f; display: block; }
  .stat-box .lbl { font-size: 10px; color: #57606a; text-transform: uppercase;
                   letter-spacing: 0.5px; display: block; margin-top: 2px; }

  h2 {
    font-size: 13px;
    font-weight: 600;
    color: #24292f;
    margin: 22px 0 8px;
    padding-left: 10px;
    border-left: 3px solid #2ea44f;
  }

  p { line-height: 1.7; margin-bottom: 8px; color: #24292f; }

  .summary-content p { font-size: 13px; }

  .two-col {
    display: flex;
    gap: 20px;
    margin: 16px 0;
  }
  .col { flex: 1; }
  .col h3 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #57606a;
    margin-bottom: 8px;
    font-weight: 600;
  }
  .col-item {
    font-size: 12px;
    color: #24292f;
    padding: 5px 0;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    align-items: flex-start;
    gap: 6px;
    line-height: 1.5;
  }

  .meta-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0;
  }
  .meta-tag {
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    color: #57606a;
  }

  .footer {
    margin-top: 50px;
    padding-top: 12px;
    border-top: 1px solid #e1e4e8;
    font-size: 10px;
    color: #8b949e;
    text-align: center;
  }
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <div class="logo">RepoInsight</div>
    <h1>Executive Summary</h1>
    <div class="sub">{{ repo.full_name }}</div>
    <div class="date">Generated {{ generated_at }}</div>
  </div>

  <div class="quality-banner">
    <span class="tier-label">{{ analysis.quality_tier }} Quality</span>
    <span class="tier-sub">Analysis performed by RepoInsight AI</span>
  </div>

  <div class="stat-row">
    <div class="stat-box">
      <span class="num">{{ repo.stars }}</span>
      <span class="lbl">Stars</span>
    </div>
    <div class="stat-box">
      <span class="num">{{ repo.forks }}</span>
      <span class="lbl">Forks</span>
    </div>
    <div class="stat-box">
      <span class="num">{{ repo.open_issues_count }}</span>
      <span class="lbl">Open Issues</span>
    </div>
  </div>

  <div class="meta-grid">
    <span class="meta-tag">{{ repo.language or 'Unknown language' }}</span>
    <span class="meta-tag">License: {{ repo.license or 'Unknown' }}</span>
  </div>

  <h2>Project Summary</h2>
  <div class="summary-content">
    {% set text = analysis.summary or '' %}
    {% for line in text.split('\n') %}
      {% set s = line.strip() %}
      {% if s and not s.startswith('#') %}
        <p>{{ s | replace('**', '') | replace('*', '') }}</p>
      {% endif %}
    {% endfor %}
  </div>

  {% if analysis.executive_summary %}
  <h2>Assessment</h2>
  <div class="summary-content">
    {% for line in analysis.executive_summary.split('\n') %}
      {% set s = line.strip() %}
      {% if s and not s.startswith('#') %}
        <p>{{ s | replace('**','') | replace('*','') }}</p>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  <div class="footer">
    Generated by RepoInsight &bull; {{ generated_at }}
  </div>
</div>
</body>
</html>
```

---

### backend/app/templates/code_quality.html (REPLACE ENTIRELY)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: #24292f;
    font-size: 13px;
  }
  .cover {
    background: #0d1117;
    color: white;
    padding: 50px;
  }
  .cover .logo { font-size: 11px; color: #2ea44f; letter-spacing: 2px;
                 text-transform: uppercase; margin-bottom: 16px; }
  .cover h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
  .cover .sub { font-size: 13px; color: #8b949e; font-family: monospace; }
  .cover .date { font-size: 11px; color: #57606a; margin-top: 8px; }

  .page { padding: 40px 50px; }

  h2 {
    font-size: 15px;
    font-weight: 600;
    color: #24292f;
    margin: 26px 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e1e4e8;
  }

  h3 {
    font-size: 13px;
    font-weight: 600;
    color: #24292f;
    margin: 14px 0 6px;
  }

  p { line-height: 1.7; margin-bottom: 8px; color: #24292f; }

  .metrics-grid {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 16px 0;
  }

  .metric-card {
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    min-width: 90px;
    flex: 1;
  }

  .metric-card .val {
    font-size: 26px;
    font-weight: 700;
    color: #24292f;
    display: block;
  }

  .metric-card .lbl {
    font-size: 10px;
    color: #57606a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: block;
    margin-top: 3px;
  }

  .issue-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid #f6f8fa;
  }

  .issue-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #fb8500;
    margin-top: 5px;
    flex-shrink: 0;
  }

  .issue-text {
    flex: 1;
  }

  .issue-title {
    font-size: 12px;
    font-weight: 500;
    color: #24292f;
  }

  .issue-file {
    font-size: 11px;
    color: #8b949e;
    font-family: monospace;
    margin-top: 1px;
  }

  .opp-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f6f8fa;
  }

  .opp-title-small { font-size: 12px; color: #24292f; font-weight: 500; }
  .opp-badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 10px;
    font-weight: 600;
  }
  .badge-beginner { background: #dafbe1; color: #2ea44f; }
  .badge-intermediate { background: #fff3e0; color: #fb8500; }
  .badge-advanced { background: #ffeef0; color: #e03e2d; }
  .opp-time { font-size: 11px; color: #8b949e; }

  .section-prose p {
    color: #24292f;
    margin-bottom: 8px;
    line-height: 1.7;
  }

  .footer {
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid #e1e4e8;
    font-size: 10px;
    color: #8b949e;
    text-align: center;
  }
</style>
</head>
<body>

<div class="cover">
  <div class="logo">RepoInsight</div>
  <h1>Code Quality Report</h1>
  <div class="sub">{{ repo.full_name }}</div>
  <div class="date">{{ generated_at }}</div>
</div>

<div class="page">

  <h2>Metrics Overview</h2>
  <div class="metrics-grid">
    <div class="metric-card">
      <span class="val">{{ metrics.files_analyzed or 0 }}</span>
      <span class="lbl">Files Analyzed</span>
    </div>
    <div class="metric-card">
      <span class="val">{{ metrics.total_functions or 0 }}</span>
      <span class="lbl">Functions</span>
    </div>
    <div class="metric-card">
      <span class="val">{{ metrics.total_classes or 0 }}</span>
      <span class="lbl">Classes</span>
    </div>
    <div class="metric-card">
      <span class="val">{{ "%.1f" | format(metrics.avg_complexity or 0) }}</span>
      <span class="lbl">Avg Complexity</span>
    </div>
    <div class="metric-card">
      <span class="val">{{ (metrics.all_issues or []) | length }}</span>
      <span class="lbl">Issues Found</span>
    </div>
  </div>

  <h2>Architecture Assessment</h2>
  <div class="section-prose">
    {% set arch = analysis.architecture_explanation or '' %}
    {% for line in arch.split('\n') %}
      {% set s = line.strip() %}
      {% if s.startswith('## ') %}
        <h3>{{ s[3:] }}</h3>
      {% elif s.startswith('**') and ':' in s %}
        <h3>{{ s | replace('**','') }}</h3>
      {% elif s.startswith('- ') or s.startswith('* ') %}
        <p style="padding-left:12px;">• {{ s[2:] | replace('**','') }}</p>
      {% elif s and not s.startswith('#') %}
        <p>{{ s | replace('**','') | replace('*','') }}</p>
      {% endif %}
    {% endfor %}
  </div>

  <h2>Common Patterns</h2>
  <div class="section-prose">
    {% set patterns = analysis.common_patterns or '' %}
    {% for line in patterns.split('\n') %}
      {% set s = line.strip() %}
      {% if s.startswith('## Common') or s.startswith('# Common') %}
        {# skip heading, we have h2 above #}
      {% elif s.startswith('## ') %}
        <h3>{{ s[3:] }}</h3>
      {% elif s.startswith('**') and ':' in s %}
        <h3>{{ s | replace('**','') }}</h3>
      {% elif s.startswith('- ') or s.startswith('* ') %}
        <p style="padding-left:12px;">• {{ s[2:] | replace('**','') }}</p>
      {% elif s and not s.startswith('#') %}
        <p>{{ s | replace('**','') | replace('*','') }}</p>
      {% endif %}
    {% endfor %}
  </div>

  {% if (metrics.all_issues or []) | length > 0 %}
  <h2>Detected Issues ({{ (metrics.all_issues or []) | length }})</h2>
  {% for issue in (metrics.all_issues or [])[:20] %}
  <div class="issue-row">
    <div class="issue-dot"></div>
    <div class="issue-text">
      <div class="issue-title">{{ issue.issue }}</div>
      <div class="issue-file">{{ issue.file }}</div>
    </div>
  </div>
  {% endfor %}
  {% endif %}

  <h2>Contribution Opportunities</h2>
  {% for opp in opportunities[:15] %}
  <div class="opp-row">
    <span class="opp-title-small">{{ opp.title }}</span>
    <span style="display:flex; gap:8px; align-items:center;">
      <span class="opp-time">⏱ {{ opp.estimated_hours }}h</span>
      <span class="opp-badge badge-{{ opp.difficulty_tier }}">{{ opp.difficulty_tier }}</span>
    </span>
  </div>
  {% endfor %}

  <div class="footer">Generated by RepoInsight &bull; repoinsight.dev &bull; {{ generated_at }}</div>

</div>
</body>
</html>
```

---

## Fix 3: PDF Service - Pass analysis as dict properly

### File: backend/app/services/pdf_service.py

The analysis object passed to templates may have None values for some fields.
Update generate_code_quality_report to extract metrics safely:

```python
def generate_code_quality_report(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    env = get_jinja_env()
    template = env.get_template("code_quality.html")

    # Extract metrics safely
    raw_metrics = analysis.get("code_quality_metrics") or {}
    if isinstance(raw_metrics, str):
        import json
        try:
            raw_metrics = json.loads(raw_metrics)
        except Exception:
            raw_metrics = {}

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        metrics=raw_metrics,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )

    filename = f"code_quality_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    HTML(string=html_content).write_pdf(str(output_path))
    return str(output_path)
```

---

## Validation Checklist

DATABASE (do this first):
[ ] Run: docker-compose exec db psql -U repoinsight -d repoinsight -c "ALTER TABLE repository_analyses ADD COLUMN IF NOT EXISTS ai_suggestions JSONB;"
[ ] Verify column exists: docker-compose exec db psql -U repoinsight -d repoinsight -c "\d repository_analyses" | grep ai_suggestions

PDF TEMPLATES:
[ ] contributor_guide.html fully replaced
[ ] executive_summary.html fully replaced  
[ ] code_quality.html fully replaced
[ ] pdf_service.py metrics extraction updated

[ ] Rebuild: docker-compose down && docker-compose up --build -d
[ ] Re-analyze a repo
[ ] Download all 3 PDF types
[ ] Verify: no raw ## or ** characters visible in PDFs
[ ] Verify: stats bar shows correct numbers
[ ] Verify: opportunities listed with tier color headers
[ ] Verify: code issues listed with orange dots
[ ] Verify: executive summary is clean single-page layout

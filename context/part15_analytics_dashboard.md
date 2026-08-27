# CONTEXT FILE: Part 15 - Analytics Dashboard
# Project: RepoInsight
# A simple no-auth analytics dashboard showing usage metrics.
# No authentication needed - this is for the owner's use.

---

## What This Part Builds

A new /dashboard page showing:
- Total repositories analyzed
- Total analyses run
- Total opportunities generated
- Total PDF reports generated
- API quota usage (Gemini + Groq)
- Most analyzed repositories
- Analysis activity over time (last 30 days)
- Tier distribution (HIGH vs MEDIUM quality analyses)
- Opportunity category breakdown
- Recent analysis activity feed

---

## Files to Create or Modify

- backend/app/routes/analytics.py     (NEW)
- backend/app/main.py                 (MODIFY - add analytics router)
- frontend/src/components/Dashboard/AnalyticsDashboard.tsx  (NEW)
- frontend/src/components/Dashboard/StatCard.tsx            (NEW)
- frontend/src/components/Dashboard/ActivityFeed.tsx        (NEW)
- frontend/src/components/Dashboard/SimpleBarChart.tsx      (NEW)
- frontend/src/api/client.ts          (MODIFY - add analytics call)
- frontend/src/App.tsx                (MODIFY - add dashboard view)
- frontend/src/components/Layout/Sidebar.tsx  (MODIFY - add dashboard nav item)

---

## Backend: Analytics Route

### backend/app/routes/analytics.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta, date

from app.database import get_db
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.models.pdf_report import PdfReport
from app.models.api_log import ApiLog

router = APIRouter()


@router.get("/analytics/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Main analytics endpoint - returns all dashboard metrics."""

    # Total repos analyzed
    total_repos = await db.scalar(
        select(func.count(Repository.id)).where(
            Repository.analysis_status == "completed"
        )
    )

    # Total analyses run
    total_analyses = await db.scalar(
        select(func.count(RepositoryAnalysis.id))
    )

    # Total opportunities generated
    total_opportunities = await db.scalar(
        select(func.count(Opportunity.id))
    )

    # Total PDFs generated
    total_pdfs = await db.scalar(
        select(func.count(PdfReport.id))
    )

    # Quality tier breakdown
    tier_result = await db.execute(
        select(
            RepositoryAnalysis.quality_tier,
            func.count(RepositoryAnalysis.id).label("count")
        )
        .group_by(RepositoryAnalysis.quality_tier)
    )
    tier_breakdown = {row.quality_tier: row.count for row in tier_result}

    # Most analyzed repos (by analysis count)
    top_repos_result = await db.execute(
        select(
            Repository.full_name,
            Repository.language,
            Repository.stars,
            func.count(RepositoryAnalysis.id).label("analysis_count")
        )
        .join(RepositoryAnalysis, RepositoryAnalysis.repo_id == Repository.id)
        .group_by(Repository.id, Repository.full_name, Repository.language, Repository.stars)
        .order_by(func.count(RepositoryAnalysis.id).desc())
        .limit(10)
    )
    top_repos = [
        {
            "full_name": row.full_name,
            "language": row.language,
            "stars": row.stars,
            "analysis_count": row.analysis_count,
        }
        for row in top_repos_result
    ]

    # Analyses per day (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_result = await db.execute(
        select(
            func.date(RepositoryAnalysis.created_at).label("day"),
            func.count(RepositoryAnalysis.id).label("count")
        )
        .where(RepositoryAnalysis.created_at >= thirty_days_ago)
        .group_by(func.date(RepositoryAnalysis.created_at))
        .order_by(func.date(RepositoryAnalysis.created_at))
    )
    daily_analyses = [
        {"date": str(row.day), "count": row.count}
        for row in daily_result
    ]

    # Opportunity category breakdown
    category_result = await db.execute(
        select(
            Opportunity.category,
            func.count(Opportunity.id).label("count")
        )
        .group_by(Opportunity.category)
        .order_by(func.count(Opportunity.id).desc())
    )
    category_breakdown = [
        {"category": row.category or "unknown", "count": row.count}
        for row in category_result
    ]

    # PDF type breakdown
    pdf_result = await db.execute(
        select(
            PdfReport.report_type,
            func.count(PdfReport.id).label("count")
        )
        .group_by(PdfReport.report_type)
    )
    pdf_breakdown = {row.report_type: row.count for row in pdf_result}

    # Language breakdown of analyzed repos
    language_result = await db.execute(
        select(
            Repository.language,
            func.count(Repository.id).label("count")
        )
        .where(Repository.analysis_status == "completed")
        .where(Repository.language.isnot(None))
        .group_by(Repository.language)
        .order_by(func.count(Repository.id).desc())
        .limit(8)
    )
    language_breakdown = [
        {"language": row.language, "count": row.count}
        for row in language_result
    ]

    # Recent analyses (activity feed)
    recent_result = await db.execute(
        select(
            Repository.full_name,
            Repository.language,
            RepositoryAnalysis.quality_tier,
            RepositoryAnalysis.created_at,
        )
        .join(RepositoryAnalysis, RepositoryAnalysis.repo_id == Repository.id)
        .order_by(RepositoryAnalysis.created_at.desc())
        .limit(10)
    )
    recent_analyses = [
        {
            "full_name": row.full_name,
            "language": row.language,
            "quality_tier": row.quality_tier,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in recent_result
    ]

    # API quota usage today
    today = date.today()
    quota_result = await db.execute(
        select(
            ApiLog.model,
            ApiLog.project,
            func.sum(ApiLog.calls_used).label("total_calls")
        )
        .where(ApiLog.date == today)
        .group_by(ApiLog.model, ApiLog.project)
    )
    quota_today = {}
    for row in quota_result:
        key = f"{row.model}_{row.project or 'default'}"
        quota_today[key] = row.total_calls

    # API calls total (all time)
    total_api_calls = await db.scalar(
        select(func.sum(ApiLog.calls_used))
    ) or 0

    return {
        "overview": {
            "total_repos_analyzed": total_repos or 0,
            "total_analyses_run": total_analyses or 0,
            "total_opportunities_generated": total_opportunities or 0,
            "total_pdfs_generated": total_pdfs or 0,
            "total_api_calls": int(total_api_calls),
        },
        "quality_tier_breakdown": tier_breakdown,
        "top_repos": top_repos,
        "daily_analyses_last_30_days": daily_analyses,
        "category_breakdown": category_breakdown,
        "pdf_type_breakdown": pdf_breakdown,
        "language_breakdown": language_breakdown,
        "recent_analyses": recent_analyses,
        "api_quota_today": quota_today,
        "generated_at": datetime.now().isoformat(),
    }
```

### Modify backend/app/main.py

Add:
```python
from app.routes.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
```

---

## Frontend Components

### frontend/src/components/Dashboard/StatCard.tsx (NEW)

```tsx
interface Props {
  label: string;
  value: number | string;
  icon: string;
  sub?: string;
  color?: string;
}

export function StatCard({ label, value, icon, sub, color = '#2ea44f' }: Props) {
  return (
    <div
      className="bg-white rounded-lg border p-5"
      style={{ borderColor: '#e1e4e8' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide mb-1"
            style={{ color: '#57606a' }}>
            {label}
          </p>
          <p className="text-3xl font-bold" style={{ color: '#24292f' }}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {sub && (
            <p className="text-xs mt-1" style={{ color: '#57606a' }}>
              {sub}
            </p>
          )}
        </div>
        <span
          className="text-2xl p-2 rounded-lg"
          style={{ backgroundColor: `${color}15` }}
        >
          {icon}
        </span>
      </div>
    </div>
  );
}
```

---

### frontend/src/components/Dashboard/SimpleBarChart.tsx (NEW)

```tsx
interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface Props {
  data: BarItem[];
  title: string;
  maxItems?: number;
}

export function SimpleBarChart({ data, title, maxItems = 8 }: Props) {
  const items = data.slice(0, maxItems);
  const max = Math.max(...items.map(d => d.value), 1);

  return (
    <div
      className="bg-white rounded-lg border p-5"
      style={{ borderColor: '#e1e4e8' }}
    >
      <h3 className="text-sm font-semibold mb-4" style={{ color: '#24292f' }}>
        {title}
      </h3>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-3">
            <div
              className="text-xs text-right flex-shrink-0"
              style={{ width: '120px', color: '#57606a' }}
            >
              {item.label}
            </div>
            <div className="flex-1 flex items-center gap-2">
              <div
                className="h-5 rounded"
                style={{
                  width: `${(item.value / max) * 100}%`,
                  backgroundColor: item.color || '#2ea44f',
                  minWidth: '4px',
                  transition: 'width 0.3s ease',
                }}
              />
              <span className="text-xs font-medium" style={{ color: '#24292f' }}>
                {item.value}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### frontend/src/components/Dashboard/ActivityFeed.tsx (NEW)

```tsx
interface Analysis {
  full_name: string;
  language: string;
  quality_tier: string;
  created_at: string;
}

interface Props {
  analyses: Analysis[];
}

function timeAgo(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function ActivityFeed({ analyses }: Props) {
  return (
    <div
      className="bg-white rounded-lg border p-5"
      style={{ borderColor: '#e1e4e8' }}
    >
      <h3 className="text-sm font-semibold mb-4" style={{ color: '#24292f' }}>
        Recent Analyses
      </h3>
      {analyses.length === 0 ? (
        <p className="text-sm" style={{ color: '#57606a' }}>
          No analyses yet.
        </p>
      ) : (
        <div className="flex flex-col gap-0">
          {analyses.map((item, i) => (
            <div
              key={i}
              className="flex items-center justify-between py-2.5"
              style={{
                borderBottom: i < analyses.length - 1 ? '1px solid #f6f8fa' : 'none'
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: item.quality_tier === 'HIGH' ? '#2ea44f' : '#fb8500'
                  }}
                />
                <div>
                  <p
                    className="text-sm font-medium"
                    style={{ color: '#24292f', fontFamily: 'monospace', fontSize: '12px' }}
                  >
                    {item.full_name}
                  </p>
                  <p className="text-xs" style={{ color: '#8b949e' }}>
                    {item.language || 'Unknown'} · {item.quality_tier} quality
                  </p>
                </div>
              </div>
              <span className="text-xs flex-shrink-0" style={{ color: '#8b949e' }}>
                {item.created_at ? timeAgo(item.created_at) : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### frontend/src/components/Dashboard/AnalyticsDashboard.tsx (NEW)

```tsx
import { useState, useEffect } from 'react';
import { StatCard } from './StatCard';
import { SimpleBarChart } from './SimpleBarChart';
import { ActivityFeed } from './ActivityFeed';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';

interface AnalyticsData {
  overview: {
    total_repos_analyzed: number;
    total_analyses_run: number;
    total_opportunities_generated: number;
    total_pdfs_generated: number;
    total_api_calls: number;
  };
  quality_tier_breakdown: Record<string, number>;
  top_repos: Array<{
    full_name: string;
    language: string;
    stars: number;
    analysis_count: number;
  }>;
  daily_analyses_last_30_days: Array<{ date: string; count: number }>;
  category_breakdown: Array<{ category: string; count: number }>;
  language_breakdown: Array<{ language: string; count: number }>;
  recent_analyses: Array<{
    full_name: string;
    language: string;
    quality_tier: string;
    created_at: string;
  }>;
  api_quota_today: Record<string, number>;
  generated_at: string;
}

export function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/analytics/overview')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load analytics');
        return res.json();
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12">
        <ErrorMessage message={error || 'Failed to load analytics'} />
      </div>
    );
  }

  const { overview, quality_tier_breakdown, api_quota_today } = data;

  // Quota calculations
  const geminiAUsed = api_quota_today['gemini-3.6-flash_project-a'] || 0;
  const geminiALimit = 100;
  const geminiAPct = Math.round((geminiAUsed / geminiALimit) * 100);

  const geminiBUsed = api_quota_today['gemini-3.6-flash_project-b'] || 0;
  const geminiBPct = Math.round((geminiBUsed / geminiALimit) * 100);

  const groqUsed = api_quota_today['openai/gpt-oss-120b_groq-project-a'] || 0;
  const groqLimit = 1000;
  const groqPct = Math.round((groqUsed / groqLimit) * 100);

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: '#f6f8fa' }}
    >
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-2xl font-bold"
            style={{ color: '#24292f', fontFamily: 'monospace' }}
          >
            Analytics Dashboard
          </h1>
          <p className="text-sm mt-1" style={{ color: '#57606a' }}>
            Last updated: {new Date(data.generated_at).toLocaleTimeString()}
          </p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 gap-4 mb-6" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <StatCard
            label="Repos Analyzed"
            value={overview.total_repos_analyzed}
            icon="📁"
            color="#2ea44f"
          />
          <StatCard
            label="Total Analyses"
            value={overview.total_analyses_run}
            icon="🔬"
            color="#0969da"
          />
          <StatCard
            label="Opportunities Found"
            value={overview.total_opportunities_generated}
            icon="🎯"
            color="#fb8500"
          />
          <StatCard
            label="PDFs Generated"
            value={overview.total_pdfs_generated}
            icon="📄"
            color="#8250df"
          />
          <StatCard
            label="Total API Calls"
            value={overview.total_api_calls}
            icon="⚡"
            color="#e03e2d"
          />
          <StatCard
            label="Analysis Quality"
            value={`${quality_tier_breakdown['HIGH'] || 0} HIGH`}
            icon="✅"
            sub={`${quality_tier_breakdown['MEDIUM'] || 0} MEDIUM`}
            color="#2ea44f"
          />
        </div>

        {/* API Quota Today */}
        <div
          className="bg-white rounded-lg border p-5 mb-6"
          style={{ borderColor: '#e1e4e8' }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: '#24292f' }}>
            API Quota Usage Today
          </h3>
          <div className="flex flex-col gap-3">
            {[
              { label: 'Gemini Project A', used: geminiAUsed, limit: geminiALimit, pct: geminiAPct, color: '#1a73e8' },
              { label: 'Gemini Project B', used: geminiBUsed, limit: geminiALimit, pct: geminiBPct, color: '#1a73e8' },
              { label: 'Groq GPT-OSS-120B', used: groqUsed, limit: groqLimit, pct: groqPct, color: '#ff4f00' },
            ].map((q) => (
              <div key={q.label}>
                <div className="flex justify-between text-xs mb-1">
                  <span style={{ color: '#24292f', fontWeight: '500' }}>{q.label}</span>
                  <span style={{ color: '#57606a' }}>
                    {q.used} / {q.limit} calls ({q.pct}%)
                  </span>
                </div>
                <div
                  className="w-full rounded-full h-2"
                  style={{ backgroundColor: '#e1e4e8' }}
                >
                  <div
                    className="h-2 rounded-full transition-all"
                    style={{
                      width: `${Math.min(q.pct, 100)}%`,
                      backgroundColor: q.pct > 80 ? '#e03e2d' : q.pct > 60 ? '#fb8500' : q.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <SimpleBarChart
            title="Opportunity Categories"
            data={data.category_breakdown.map(c => ({
              label: c.category,
              value: c.count,
              color: '#2ea44f',
            }))}
          />
          <SimpleBarChart
            title="Repository Languages"
            data={data.language_breakdown.map(l => ({
              label: l.language,
              value: l.count,
              color: '#0969da',
            }))}
          />
        </div>

        {/* Activity + Top Repos Row */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ActivityFeed analyses={data.recent_analyses} />

          {/* Top Repos */}
          <div
            className="bg-white rounded-lg border p-5"
            style={{ borderColor: '#e1e4e8' }}
          >
            <h3 className="text-sm font-semibold mb-4" style={{ color: '#24292f' }}>
              Most Analyzed Repositories
            </h3>
            <div className="flex flex-col gap-0">
              {data.top_repos.slice(0, 8).map((repo, i) => (
                <div
                  key={repo.full_name}
                  className="flex items-center justify-between py-2"
                  style={{
                    borderBottom: i < data.top_repos.length - 1 ? '1px solid #f6f8fa' : 'none'
                  }}
                >
                  <div>
                    <p
                      className="text-xs font-medium"
                      style={{ color: '#24292f', fontFamily: 'monospace' }}
                    >
                      {repo.full_name}
                    </p>
                    <p className="text-xs" style={{ color: '#8b949e' }}>
                      {repo.language} · ⭐ {repo.stars}
                    </p>
                  </div>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: '#f6f8fa', color: '#57606a' }}
                  >
                    {repo.analysis_count}x
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Daily Activity Chart */}
        {data.daily_analyses_last_30_days.length > 0 && (
          <div
            className="bg-white rounded-lg border p-5"
            style={{ borderColor: '#e1e4e8' }}
          >
            <h3 className="text-sm font-semibold mb-4" style={{ color: '#24292f' }}>
              Analyses — Last 30 Days
            </h3>
            <SimpleBarChart
              title=""
              data={data.daily_analyses_last_30_days.map(d => ({
                label: d.date.slice(5),
                value: d.count,
                color: '#2ea44f',
              }))}
              maxItems={30}
            />
          </div>
        )}

      </div>
    </div>
  );
}
```

---

## Frontend Integration

### Modify frontend/src/api/client.ts

Add:
```typescript
export const getAnalytics = async () => {
  const res = await api.get('/analytics/overview');
  return res.data;
};
```

### Modify frontend/src/App.tsx

Add 'dashboard' to the View type:
```typescript
type View = 'home' | 'results' | 'repos' | 'dashboard';
```

Add import:
```typescript
import { AnalyticsDashboard } from './components/Dashboard/AnalyticsDashboard';
```

Add to JSX (after the repos view block):
```tsx
{view === 'dashboard' && <AnalyticsDashboard />}
```

### Modify frontend/src/components/Layout/Sidebar.tsx

Add dashboard nav item after "Recent Repos":
```tsx
<NavItem
  label="Analytics"
  icon="📊"
  active={currentView === 'dashboard'}
  onClick={() => onNavigate('dashboard')}
/>
```

---

## Validation Checklist

[ ] backend/app/routes/analytics.py created
[ ] analytics_router added to main.py
[ ] All 4 frontend dashboard components created in correct paths
[ ] api/client.ts has getAnalytics function
[ ] App.tsx has 'dashboard' in View type
[ ] App.tsx renders AnalyticsDashboard for dashboard view
[ ] Sidebar.tsx has Analytics nav item
[ ] Rebuild: docker-compose down && docker-compose up --build -d
[ ] Click Analytics in sidebar - dashboard loads
[ ] Stat cards show correct numbers from DB
[ ] API quota bars show today's usage
[ ] Activity feed shows recent analyses
[ ] Top repos list shows most analyzed repos
[ ] No errors in browser console
[ ] GET /api/analytics/overview returns valid JSON

Test curl:
curl http://localhost:8000/api/analytics/overview

Expected: JSON with overview, quality_tier_breakdown, top_repos, etc.

import { useState, useEffect } from 'react';
import { StatCard } from './StatCard';
import { SimpleBarChart } from './SimpleBarChart';
import { ActivityFeed } from './ActivityFeed';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';
import { getAnalytics } from '../../api/client';

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
    getAnalytics()
      .then(setData)
      .catch((e: any) => {
        console.error('Failed to load analytics:', e);
        setError(e?.response?.data?.detail || e?.message || 'Failed to load analytics');
      })
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

  const { overview, quality_tier_breakdown } = data;

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-2xl font-bold"
            style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}
          >
            Analytics Dashboard
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
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

import { StatCard } from './StatCard';
import { SimpleBarChart } from './SimpleBarChart';
import { ActivityFeed } from './ActivityFeed';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';
import { getAnalytics } from '../../api/client';
import { useCachedFetch } from '../../hooks/useCachedFetch';

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
  const { data, loading, error, slow, reload } = useCachedFetch<AnalyticsData>('analytics_cache_v1', getAnalytics);

  if (!data && loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <LoadingSpinner size="lg" />
        {slow && (
          <p className="text-xs text-muted" style={{ color: 'var(--text-muted)' }}>
            Server is waking up (free hosting). This can take up to a minute...
          </p>
        )}
      </div>
    );
  }

  if (!data && error) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 flex flex-col items-center gap-4">
        <ErrorMessage message={error} />
        <button
          onClick={reload}
          className="px-4 py-2 text-xs font-medium rounded text-white"
          style={{ backgroundColor: 'var(--color-primary, #0969da)' }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { overview, quality_tier_breakdown } = data;

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Cache status banners */}
        {loading && (
          <div className="mb-4 px-3 py-1.5 rounded text-xs" style={{ backgroundColor: '#fff8e1', color: '#8a6d00' }}>
            Refreshing...
          </div>
        )}
        {error && (
          <div className="mb-4 px-3 py-1.5 rounded text-xs flex items-center justify-between" style={{ backgroundColor: '#ffeef0', color: '#b42318' }}>
            <span>Showing last saved data. Server unreachable.</span>
            <button onClick={reload} className="font-semibold underline ml-2">
              Retry
            </button>
          </div>
        )}

        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-2xl font-bold"
            style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}
          >
            Analytics Dashboard
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Last updated: {
              new Date(
                !data.generated_at.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(data.generated_at)
                  ? `${data.generated_at}Z`
                  : data.generated_at
              ).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })
            } (IST)
          </p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 gap-4 mb-6" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <StatCard
            label="Repos Analyzed"
            value={overview.total_repos_analyzed}
          />
          <StatCard
            label="Total Analyses"
            value={overview.total_analyses_run}
          />
          <StatCard
            label="Opportunities Found"
            value={overview.total_opportunities_generated}
          />
          <StatCard
            label="PDFs Generated"
            value={overview.total_pdfs_generated}
          />
          <StatCard
            label="Total API Calls"
            value={overview.total_api_calls}
          />
          <StatCard
            label="Analysis Quality"
            value={`${quality_tier_breakdown['HIGH'] || 0} HIGH`}
            sub={`${quality_tier_breakdown['MEDIUM'] || 0} MEDIUM`}
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

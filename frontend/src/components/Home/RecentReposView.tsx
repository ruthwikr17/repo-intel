import { listRepos } from '../../api/client';
import { useCachedFetch } from '../../hooks/useCachedFetch';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';

export function RecentReposView() {
  const { data, loading, error, slow, reload } = useCachedFetch('recent_repos_cache_v1', listRepos);
  const repos = data?.repositories ?? [];

  if (!data && loading) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 flex flex-col items-center justify-center gap-3">
        <LoadingSpinner size="lg" />
        {slow && (
          <p className="text-xs" style={{ color: 'var(--text-muted, #57606a)' }}>
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

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
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
      <h2
        className="text-xl font-bold mb-6"
        style={{ color: '#24292f', fontFamily: 'monospace' }}
      >
        Recently Analyzed
      </h2>
      {repos.length === 0 ? (
        <p style={{ color: '#57606a' }}>No repositories analyzed yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {repos.map((repo) => (
            <div
              key={repo.id}
              className="bg-white rounded border p-4"
              style={{ borderColor: '#e1e4e8' }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="font-medium text-sm"
                  style={{ color: '#24292f', fontFamily: 'monospace' }}
                >
                  {repo.full_name}
                </span>
                <span className="text-xs" style={{ color: '#57606a' }}>
                  ⭐ {repo.stars}
                </span>
              </div>
              {repo.description && (
                <p
                  className="text-xs mt-1"
                  style={{ color: '#57606a' }}
                >
                  {repo.description.slice(0, 100)}
                </p>
              )}
              <p className="text-xs mt-2" style={{ color: '#8b949e' }}>
                {repo.language} &bull; Analyzed{' '}
                {new Date(repo.last_analyzed_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

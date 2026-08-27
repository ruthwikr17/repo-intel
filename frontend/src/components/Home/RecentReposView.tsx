import { useState, useEffect } from 'react';
import { listRepos } from '../../api/client';

export function RecentReposView() {
  const [repos, setRepos] = useState<any[]>([]);

  useEffect(() => {
    listRepos().then((data) => setRepos(data.repositories));
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
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

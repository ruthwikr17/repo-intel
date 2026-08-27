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

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

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

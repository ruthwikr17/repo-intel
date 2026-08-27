const COLORS = {
  beginner: { bg: '#dafbe1', text: '#2ea44f', border: '#9be9a8' },
  intermediate: { bg: '#fff3e0', text: '#fb8500', border: '#ffcc80' },
  advanced: { bg: '#ffeef0', text: '#e03e2d', border: '#ffc1c0' },
};

export function DifficultyBadge({
  tier,
}: {
  tier: 'beginner' | 'intermediate' | 'advanced';
}) {
  const color = COLORS[tier] || COLORS.intermediate;
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full border font-medium capitalize"
      style={{
        backgroundColor: color.bg,
        color: color.text,
        borderColor: color.border,
      }}
    >
      {tier}
    </span>
  );
}

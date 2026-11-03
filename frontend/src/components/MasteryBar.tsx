interface Props {
  score: number;       // 0–100
  label: string;
  status: string;
  showLabel?: boolean;
}

const statusColors: Record<string, { bar: string; bg: string; text: string }> = {
  mastered:          { bar: 'bg-emerald-500', bg: 'bg-emerald-50',  text: 'text-emerald-700' },
  working_towards:   { bar: 'bg-amber-400',   bg: 'bg-amber-50',    text: 'text-amber-700' },
  needs_attention:   { bar: 'bg-red-500',      bg: 'bg-red-50',      text: 'text-red-700' },
  not_started:       { bar: 'bg-gray-300',     bg: 'bg-gray-50',     text: 'text-gray-500' },
};

export default function MasteryBar({ score, label, status, showLabel = true }: Props) {
  const colors = statusColors[status] || statusColors.not_started;
  const clampedScore = Math.max(0, Math.min(100, score));

  return (
    <div className="space-y-1.5">
      {showLabel && (
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
            {clampedScore.toFixed(0)}%
          </span>
        </div>
      )}
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full ${colors.bar} transition-all duration-500`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
    </div>
  );
}


interface AgentProgressBarProps {
  current: number;
  total: number;
}

export function AgentProgressBar({ current, total }: AgentProgressBarProps) {
  const pct = total > 0 ? Math.min(100, (current / total) * 100) : 0;
  return (
    <div className="progressbar">
      <div
        className="progressbar__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={current}
      >
        <div className="progressbar__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progressbar__label">
        Iteración {current} / {total || '—'}
      </span>
    </div>
  );
}

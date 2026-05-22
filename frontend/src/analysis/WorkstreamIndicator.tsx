import { useMemo } from 'react';
import { useConfigStore } from '@/state/configStore';

interface WorkstreamIndicatorProps {
  activeWorkstreams?: string[];
}

export function WorkstreamIndicator({ activeWorkstreams }: WorkstreamIndicatorProps) {
  const ws = useConfigStore((s) => s.workstreams);
  const configActive = useMemo(() => {
    const out: string[] = [];
    if (ws.wsA) out.push('WS-A');
    if (ws.wsB) out.push('WS-B');
    if (ws.wsC) out.push('WS-C');
    if (ws.wsD) out.push('WS-D');
    if (ws.wsE) out.push('WS-E');
    return out;
  }, [ws]);

  const active = activeWorkstreams ?? configActive;

  if (active.length === 0) {
    return <span className="ws-indicator ws-indicator--empty">Sin workstreams activos</span>;
  }

  return (
    <span className="ws-indicator">
      {active.map((label) => (
        <span key={label} className="ws-indicator__badge" title={label}>
          {label}
        </span>
      ))}
    </span>
  );
}

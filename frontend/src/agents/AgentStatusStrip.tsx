import type { BranchAgent, BranchType } from '@/types';
import { getBranchLabel } from '@/graph/graphUtils';

interface AgentStatusStripProps {
  agents: BranchAgent[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

function abbr(branch: BranchType): string {
  return getBranchLabel(branch).slice(0, 4).toUpperCase();
}

export function AgentStatusStrip({
  agents,
  selectedIndex,
  onSelect,
}: AgentStatusStripProps) {
  return (
    <div className="statusstrip" role="tablist" aria-label="Estado de agentes">
      {agents.map((agent, i) => (
        <button
          key={agent.branchType}
          type="button"
          role="tab"
          aria-selected={i === selectedIndex}
          className="statusstrip__cell"
          title={`${getBranchLabel(agent.branchType)} — ${agent.status}`}
          onClick={() => onSelect(i)}
        >
          <span
            className="statusstrip__dial"
            data-status={agent.status}
            aria-hidden="true"
          />
          <span className="statusstrip__abbr">{abbr(agent.branchType)}</span>
        </button>
      ))}
    </div>
  );
}

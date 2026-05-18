import type { BranchAgent } from '@/types';
import { Button, Icon, StateBlock } from '@/components';
import { useAgentsStore } from '@/state/agentsStore';
import { AgentStatusStrip } from './AgentStatusStrip';
import { AgentDetailPanel } from './AgentDetailPanel';
import { ReplanSignals } from './ReplanSignals';

interface AgentSidebarProps {
  agents: BranchAgent[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onClose: () => void;
}

export function AgentSidebar({
  agents,
  selectedIndex,
  onSelect,
  onClose,
}: AgentSidebarProps) {
  const safeIndex = Math.max(0, Math.min(selectedIndex, agents.length - 1));
  const current = agents[safeIndex];
  const replanSignals = useAgentsStore((s) => s.replanSignals);

  return (
    <aside className="agentbar" aria-label="Observatorio de agentes">
      <div className="agentbar__head">
        <span className="agentbar__head-title">Observatorio de agentes</span>
        <button
          type="button"
          className="btn btn--icon"
          onClick={onClose}
          aria-label="Ocultar observatorio"
        >
          <Icon name="panel" size={15} />
        </button>
      </div>

      {agents.length === 0 ? (
        <StateBlock
          kind="empty"
          glyph="SIN DESPACHO"
          title="Ningún agente activo"
          hint="Los seis investigadores aparecerán aquí cuando se apruebe un plan de investigación."
        />
      ) : (
        <>
          <AgentStatusStrip
            agents={agents}
            selectedIndex={safeIndex}
            onSelect={onSelect}
          />
          <ReplanSignals signals={replanSignals} />
          {current && (
            <>
              <div className="agentdetail__nav" style={{ paddingBottom: 10 }}>
                <span className="agentdetail__meta" style={{ border: 0, padding: 0 }}>
                  Agente {safeIndex + 1} de {agents.length}
                </span>
                <div className="agentdetail__navbtns">
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Agente anterior"
                    disabled={safeIndex === 0}
                    onClick={() => onSelect(safeIndex - 1)}
                  >
                    <Icon name="arrow-left" size={14} />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Agente siguiente"
                    disabled={safeIndex === agents.length - 1}
                    onClick={() => onSelect(safeIndex + 1)}
                  >
                    <Icon name="arrow-right" size={14} />
                  </Button>
                </div>
              </div>
              <AgentDetailPanel agent={current} />
            </>
          )}
        </>
      )}
    </aside>
  );
}

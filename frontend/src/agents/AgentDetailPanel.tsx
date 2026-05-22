import type { BranchAgent, BranchAgentStatus } from '@/types';
import { Badge } from '@/components';
import { getBranchColor, getBranchLabel } from '@/graph/graphUtils';
import { AgentIterationCard } from './AgentIterationCard';
import { AgentProgressBar } from './AgentProgressBar';

interface AgentDetailPanelProps {
  agent: BranchAgent;
}

const STATUS_TONE: Record<
  BranchAgentStatus,
  'info' | 'warning' | 'success' | 'error'
> = {
  waiting: 'info',
  running: 'warning',
  completed: 'success',
  failed: 'error',
};

const STATUS_LABEL: Record<BranchAgentStatus, string> = {
  waiting: 'En espera',
  running: 'Ejecutando',
  completed: 'Completado',
  failed: 'Fallido',
};

export function AgentDetailPanel({ agent }: AgentDetailPanelProps) {
  return (
    <div className="agentdetail">
      <div className="agentdetail__nav">
        <span className="agentdetail__name">
          <span
            className="agentdetail__name-swatch"
            style={{ background: getBranchColor(agent.branchType) }}
            aria-hidden="true"
          />
          {getBranchLabel(agent.branchType)}
        </span>
        <Badge tone={STATUS_TONE[agent.status]}>
          {STATUS_LABEL[agent.status]}
        </Badge>
      </div>

      <div className="agentdetail__meta">
        <span>Confianza {Math.round(agent.confidence * 100)}%</span>
        <span>·</span>
        <span>{agent.iterations.length} iteraciones</span>
      </div>

      {agent.status === 'running' && (
        <div style={{ padding: '12px 16px 0' }}>
          <AgentProgressBar
            current={agent.currentIteration}
            total={agent.totalIterations}
          />
        </div>
      )}

      <div className="agentdetail__iters">
        {agent.status === 'failed' && agent.error && (
          <div
            className="badge badge--error"
            style={{ alignSelf: 'flex-start' }}
          >
            <span className="badge__dot" aria-hidden="true" />
            {agent.error}
          </div>
        )}
        {agent.iterations.length === 0 ? (
          <p
            style={{
              fontFamily: 'var(--serif-body)',
              fontSize: 13,
              fontStyle: 'italic',
              color: 'var(--ink-faint)',
              textAlign: 'center',
              padding: '28px 12px',
            }}
          >
            {agent.status === 'waiting'
              ? 'Agente en espera de despacho.'
              : 'Aún sin iteraciones registradas.'}
          </p>
        ) : (
          <div className="iterchain">
            {agent.iterations.map((step, i) => (
              <AgentIterationCard
                key={step.stepNumber}
                step={step}
                isLast={i === agent.iterations.length - 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

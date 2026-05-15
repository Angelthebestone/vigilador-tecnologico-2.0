import type { ReactNode } from 'react';
import type { ResearchPlan } from '@/types';
import { Button } from '@/components';
import { getBranchColor, getBranchLabel } from '@/graph/graphUtils';

interface PlanBlockProps {
  plan: ResearchPlan;
  /** Cadena de pensamiento del planner (PlanningChain), inyectada por el contenedor. */
  thinkingChain?: ReactNode;
  disabled?: boolean;
  approved?: boolean;
  onApprove: () => void;
  onModify: () => void;
}

export function PlanBlock({
  plan,
  thinkingChain,
  disabled = false,
  approved = false,
  onApprove,
  onModify,
}: PlanBlockProps) {
  return (
    <div className="plan">
      <div className="plan__head">
        <span className="plan__title">
          <small>Plan de investigación · v{plan.version}</small>
          {plan.branches.length} ramas trazadas
        </span>
        <span
          className={`badge badge--${approved ? 'success' : 'warning'}`}
          style={{ marginLeft: 'auto' }}
        >
          <span className="badge__dot" aria-hidden="true" />
          {approved ? 'Aprobado' : 'Pendiente de aprobación'}
        </span>
      </div>

      {thinkingChain && <div style={{ padding: '14px 18px 0' }}>{thinkingChain}</div>}

      <ol className="plan__branches">
        {plan.branches.map((branch, i) => (
          <li className="plan__branch" key={branch.branchType}>
            <span className="plan__branch-idx">{i + 1}</span>
            <div>
              <div className="plan__branch-name">
                <span
                  className="plan__branch-swatch"
                  style={{ background: getBranchColor(branch.branchType) }}
                  aria-hidden="true"
                />
                {getBranchLabel(branch.branchType)}
              </div>
              <div className="plan__queries">
                {branch.focusQueries.join(' · ')}
              </div>
              <div className="plan__providers">
                {branch.mcpProviders.map((p) => (
                  <span className="plan__provider" key={p}>
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ol>

      {!approved && (
        <div className="plan__actions">
          <Button
            variant="primary"
            disabled={disabled}
            onClick={onApprove}
          >
            Aprobar y ejecutar
          </Button>
          <Button variant="ghost" disabled={disabled} onClick={onModify}>
            Modificar
          </Button>
        </div>
      )}
    </div>
  );
}

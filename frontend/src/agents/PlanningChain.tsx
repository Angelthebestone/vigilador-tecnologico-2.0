import type { ThinkingStep } from '@/types';
import { CollapsibleSection } from '@/components';

interface PlanningChainProps {
  steps: ThinkingStep[];
  branchCount: number;
  ready?: boolean;
}

export function PlanningChain({
  steps,
  branchCount,
  ready = true,
}: PlanningChainProps) {
  const summary = (
    <span>
      Razonamiento del planificador — {branchCount} ramas
      {ready ? ' · listo para aprobar' : ' · en proceso'}
    </span>
  );

  return (
    <CollapsibleSection marker="§ PLAN" summary={summary}>
      {steps.length === 0 ? (
        <p
          style={{
            fontFamily: 'var(--serif-body)',
            fontSize: 13,
            fontStyle: 'italic',
            color: 'var(--ink-faint)',
          }}
        >
          Sin pasos de razonamiento registrados.
        </p>
      ) : (
        steps.map((step) => (
          <div className="thinking__step" key={step.stepNumber}>
            <span className="thinking__num">
              {String(step.stepNumber).padStart(2, '0')}
            </span>
            <div>
              <div className="thinking__reason">{step.reasoning}</div>
              {step.toolCall && (
                <div className="thinking__tool">
                  {step.toolCall.tool} · «{step.toolCall.query}»
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}

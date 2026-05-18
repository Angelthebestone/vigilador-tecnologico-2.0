import type { ReplanSignal } from '@/types';
import { Icon, CollapsibleSection } from '@/components';
import { getBranchLabel } from '@/graph/graphUtils';

interface ReplanSignalsProps {
  signals: ReplanSignal[];
}

/** Coordinación reactiva: el BranchCoordinator redirige una directiva de una
 *  rama a otra a mitad de ejecución cuando una rama emite una señal
 *  (gap/entidad). No es un agente "planner" ni el LLM — es orquestación.
 *  Compactado a una línea-resumen colapsable para no romper el flujo
 *  selector→detalle del observatorio. */
export function ReplanSignals({ signals }: ReplanSignalsProps) {
  if (signals.length === 0) return null;

  return (
    <div className="replan">
      <CollapsibleSection
        marker="⟲"
        summary={
          <span className="replan__summary">
            Coordinación reactiva
            <span className="replan__count">{signals.length}</span>
          </span>
        }
      >
        <ul className="replan__list">
          {signals.map((s, i) => (
            <li className="replan__item" key={i}>
              <div className="replan__route">
                {getBranchLabel(s.sourceBranch)}
                <Icon name="arrow-right" size={12} />
                {getBranchLabel(s.targetBranch)}
                <span className="replan__tag">{s.signalType}</span>
              </div>
              <div className="replan__desc">{s.description}</div>
              <div className="replan__directive">{s.directive}</div>
            </li>
          ))}
        </ul>
      </CollapsibleSection>
    </div>
  );
}

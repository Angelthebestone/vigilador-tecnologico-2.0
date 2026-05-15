import { useId, useState } from 'react';
import type { ThinkingStep } from '@/types';
import { Icon } from '@/components';

interface AgentIterationCardProps {
  step: ThinkingStep;
}

export function AgentIterationCard({ step }: AgentIterationCardProps) {
  const [open, setOpen] = useState(false);
  const bodyId = useId();

  return (
    <article className="itercard" data-open={open}>
      <button
        type="button"
        className="itercard__head"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="itercard__step">
          {String(step.stepNumber).padStart(2, '0')}
        </span>
        <span className="itercard__tool">
          {step.toolCall ? step.toolCall.tool : 'razonamiento'}
        </span>
        <span className="itercard__conf">
          {Math.round(step.confidence * 100)}%
        </span>
        <Icon name="chevron" size={13} className="itercard__chevron" />
      </button>
      <div className="itercard__body" id={bodyId} aria-hidden={!open}>
        <div>
          <div className="itercard__inner">
            <div>
              <div className="iterrow__k">Razonamiento</div>
              <div className="iterrow__v">{step.reasoning}</div>
            </div>
            {step.toolCall && (
              <>
                <div>
                  <div className="iterrow__k">Consulta</div>
                  <div className="iterrow__v">
                    <code>{step.toolCall.query}</code>
                  </div>
                </div>
                <div>
                  <div className="iterrow__k">Respuesta</div>
                  <div className="iterrow__v">{step.toolCall.result}</div>
                </div>
              </>
            )}
            {step.result && (
              <div>
                <div className="iterrow__k">Hallazgo intermedio</div>
                <div className="iterrow__v">{step.result}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

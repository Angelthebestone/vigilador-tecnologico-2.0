import { useId, useState } from 'react';
import type { ThinkingStep } from '@/types';
import { Icon } from '@/components';

interface AgentIterationCardProps {
  step: ThinkingStep;
  /** true si es el último paso de la cadena (no dibuja conector inferior). */
  isLast?: boolean;
}

/**
 * Una iteración del agente se presenta como un eslabón de una cadena de
 * pensamiento: un nodo numerado conectado por un riel vertical al
 * siguiente paso. El razonamiento del agente va por fuera, siempre
 * visible (texto natural, como un agente que piensa en voz alta). La
 * tool call es una tarjeta técnica colapsable que solo muestra su
 * entrada y salida. El hallazgo cierra el turno.
 *
 * Los hallazgos — incluso observaciones críticas o negativas — se
 * muestran en verde: un riesgo detectado sigue siendo una conclusión
 * válida del razonamiento, no un error del sistema.
 */
export function AgentIterationCard({ step, isLast = false }: AgentIterationCardProps) {
  const [toolOpen, setToolOpen] = useState(false);
  const toolBodyId = useId();

  return (
    <article className={`iterstep ${isLast ? 'iterstep--last' : ''}`}>
      {/* Riel de cadena de pensamiento: nodo numerado + línea conectora */}
      <div className="iterstep__rail" aria-hidden="true">
        <div className="iterstep__node">{step.stepNumber}</div>
        {!isLast && <div className="iterstep__line" />}
      </div>

      <div className="iterstep__content">
        {/* Razonamiento del agente — pensamiento en voz alta, siempre visible */}
        <div className="iterstep__reasoning">{step.reasoning}</div>

        {/* Tool call — tarjeta técnica colapsable, solo entrada/salida */}
        {step.toolCall && (
          <div className="toolcall" data-open={toolOpen}>
            <button
              type="button"
              className="toolcall__head"
              aria-expanded={toolOpen}
              aria-controls={toolBodyId}
              onClick={() => setToolOpen((v) => !v)}
            >
              <Icon name="flask" size={12} className="toolcall__icon" />
              <span className="toolcall__tool">{step.toolCall.tool}</span>
              <span className="toolcall__conf">{Math.round(step.confidence * 100)}%</span>
              <Icon name="chevron" size={12} className="toolcall__chevron" />
            </button>
            <div className="toolcall__body" id={toolBodyId} aria-hidden={!toolOpen}>
              <div>
                <div className="toolcall__inner">
                  <div className="toolcall__row">
                    <span className="toolcall__k">Consulta</span>
                    <code className="toolcall__query">{step.toolCall.query}</code>
                  </div>
                  {step.toolCall.code && (
                    <div className="toolcall__row">
                      <span className="toolcall__k">Código ejecutado</span>
                      <pre className="toolcall__code">
                        <code>{step.toolCall.code}</code>
                      </pre>
                    </div>
                  )}
                  {step.toolCall.stdout && (
                    <div className="toolcall__row">
                      <span className="toolcall__k">Salida (stdout)</span>
                      <pre className="toolcall__code">
                        <code>{step.toolCall.stdout}</code>
                      </pre>
                    </div>
                  )}
                  {step.toolCall.image && (
                    <div className="toolcall__row">
                      <span className="toolcall__k">Visualización generada</span>
                      <img
                        className="toolcall__img"
                        src={step.toolCall.image}
                        alt={`Gráfico generado: ${step.toolCall.query}`}
                        loading="lazy"
                      />
                    </div>
                  )}
                  <div className="toolcall__row">
                    <span className="toolcall__k">Resultado de la herramienta</span>
                    <span className="toolcall__result">{step.toolCall.result}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Conclusión del paso — texto neutro, sin marca de estado */}
        {step.result && (
          <div className="iterstep__finding">
            <span>{step.result}</span>
          </div>
        )}
      </div>
    </article>
  );
}

import type { WseResult } from '@/types';
import { WorkstreamSection } from './WorkstreamSection';
import { ChartImage } from './ChartImage';

interface WSESectionProps {
  data: WseResult;
}

const STAKEHOLDER_META: Record<string, { label: string; perspective: string; color: string }> = {
  investor: {
    label: 'Inversor',
    perspective: 'Evalúa rentabilidad, riesgo financiero y horizonte de retorno',
    color: 'var(--lime-deep)',
  },
  regulator: {
    label: 'Regulador',
    perspective: 'Analiza cumplimiento normativo, riesgos sistémicos y protección pública',
    color: 'var(--uts-green)',
  },
  competitor: {
    label: 'Competidor',
    perspective: 'Detecta ventajas competitivas, brechas de mercado y amenazas',
    color: 'var(--gray-dark)',
  },
  academic: {
    label: 'Académico',
    perspective: 'Cuestiona rigor metodológico, validez de muestras y generalizabilidad',
    color: 'var(--uts-green-deep)',
  },
};

/** Barra de distribución horizontal — usada en la auditoría de sesgos. */
function DistributionBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="ws-dist-row">
      <span className="ws-dist-row__label">{label}</span>
      <div className="ws-dist-row__track">
        <div
          className="ws-dist-row__fill"
          style={{ width: `${Math.round(value * 100)}%`, background: color }}
        />
      </div>
      <span className="ws-dist-row__value">{Math.round(value * 100)}%</span>
    </div>
  );
}

export function WSESection({ data }: WSESectionProps) {
  return (
    <WorkstreamSection title="Garantía de calidad (WS-E)" icon="shield" status="active">

      {!data.qualityGatePassed && (
        <div className="ws-alert ws-alert--danger">
          El control de calidad detectó problemas críticos en el análisis. Los hallazgos deben
          revisarse antes de usarse para toma de decisiones.
        </div>
      )}

      {data.biasAudit && (
        <div className="ws-block">
          <h4>
            Auditoría de sesgos{' '}
            <span className={`badge ${data.biasAudit.criticalBiasDetected ? 'badge--alert' : 'badge--success'}`}>
              {data.biasAudit.criticalBiasDetected ? 'Sesgo crítico detectado' : 'Sin sesgos críticos'}
            </span>
          </h4>
          <p className="ws-explain">
            Analiza si las fuentes del corpus presentan distribuciones desequilibradas por
            geografía, género institucional o tipo de institución, lo que podría sesgar las conclusiones.
          </p>
          <div className="ws-distribution">
            <div className="ws-dist-group">
              <strong>Distribución geográfica</strong>
              {Object.entries(data.biasAudit.geographicDistribution).map(([k, v]) => (
                <DistributionBar key={k} label={k} value={v} color="var(--lime)" />
              ))}
            </div>
            <div className="ws-dist-group">
              <strong>Distribución por género</strong>
              {Object.entries(data.biasAudit.genderDistribution).map(([k, v]) => (
                <DistributionBar key={k} label={k} value={v} color="var(--uts-green)" />
              ))}
            </div>
            <div className="ws-dist-group">
              <strong>Tipo de institución</strong>
              {Object.entries(data.biasAudit.institutionalDistribution).map(([k, v]) => (
                <DistributionBar key={k} label={k} value={v} color="var(--gray-dark)" />
              ))}
            </div>
          </div>
        </div>
      )}

      {data.stakeholderSimulations.length > 0 && (
        <div className="ws-block">
          <h4>Simulación de perspectivas de stakeholders</h4>
          <p className="ws-explain">
            Cada perfil analiza el informe desde su rol e intereses específicos, identificando
            puntos ciegos, objeciones potenciales y argumentos de contrapeso. Ayuda a anticipar
            cómo diferentes audiencias recibirán los hallazgos.
          </p>
          <div className="ws-stakeholder-list">
            {data.stakeholderSimulations.map((s, i) => {
              const meta = STAKEHOLDER_META[s.stakeholderType] ?? {
                label: s.stakeholderType,
                perspective: '',
                color: 'var(--gray-dark)',
              };
              return (
                <div key={i} className="ws-stakeholder-card">
                  <div className="ws-stakeholder-card__header">
                    <span
                      className="ws-stakeholder-card__role"
                      style={{ color: meta.color }}
                    >
                      {meta.label}
                    </span>
                  </div>
                  {meta.perspective && (
                    <p className="ws-stakeholder-card__perspective">{meta.perspective}</p>
                  )}
                  <div className="ws-stakeholder-card__critique">{s.critique}</div>
                  {s.counterpoints.length > 0 && (
                    <>
                      <div className="ws-stakeholder-card__counterpoints-label">
                        Argumentos de contrapeso
                      </div>
                      <ul className="ws-list">
                        {s.counterpoints.map((cp, j) => <li key={j}>{cp}</li>)}
                      </ul>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.falsificationScenarios.length > 0 && (
        <div className="ws-block">
          <h4>Escenarios de falsificación</h4>
          <p className="ws-explain">
            Condiciones específicas bajo las cuales las conclusiones principales del informe
            serían inválidas. Identificarlas fortalece la robustez del análisis.
          </p>
          <div className="ws-counterfactual-list">
            {data.falsificationScenarios.map((f, i) => (
              <div key={i} className="ws-counterfactual">
                <div className="ws-counterfactual__scenario">{f.scenario}</div>
                <div className="ws-counterfactual__meta">
                  <span className={`badge badge--sm ${f.plausibility === 'high' ? 'badge--alert' : f.plausibility === 'medium' ? 'badge--warning' : 'badge--info'}`}>
                    Plausibilidad {f.plausibility === 'high' ? 'alta' : f.plausibility === 'medium' ? 'media' : 'baja'}
                  </span>
                  {f.wouldInvalidate && (
                    <span className="ws-counterfactual__invalidates">
                      Invalidaría: {f.wouldInvalidate}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.forensicTraces.length > 0 && (
        <div className="ws-block">
          <h4>Trazabilidad forense de hallazgos</h4>
          <p className="ws-explain">
            Registra la cadena de evidencia de cada hallazgo: de dónde se extrajo,
            qué razonamiento lo derivó y con qué nivel de confianza en cada paso.
          </p>
          {data.forensicTraces.map((t, i) => (
            <div key={i} className="ws-trace">
              <div className="ws-trace__claim">Hallazgo: {t.claimId}</div>
              <div className="ws-trace__steps">
                {t.traceSteps.map((s, j) => (
                  <div key={j} className="ws-trace__step">
                    <span className="badge badge--sm badge--info">{s.stepType}</span>
                    {' '}{s.description}
                    <span className="ws-trace__conf">conf. {Math.round(s.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {data.calibrationCurve && (
        <div className="ws-block">
          <h4>Curva de calibración de confianza</h4>
          <p className="ws-explain">
            Muestra si los niveles de confianza del informe son realistas. Una calibración
            perfecta significaría que cuando el modelo dice "80% de confianza", acierta el
            80% de las veces. El modelo fue entrenado con {data.calibrationCurve.samplesCount} muestras.
          </p>
          {data.calibrationCurve.chartImage ? (
            <ChartImage
              src={data.calibrationCurve.chartImage}
              alt="Curva de calibración de confianza"
              caption="La diagonal representa calibración perfecta; los puntos sobre ella indican sobreconfianza, por debajo infraconfianza."
            />
          ) : (
            <table className="ws-table ws-table--sm">
              <thead>
                <tr><th>Confianza predicha</th><th>Confianza calibrada</th></tr>
              </thead>
              <tbody>
                {data.calibrationCurve.curvePoints.map((p, i) => (
                  <tr key={i}>
                    <td>{Math.round(p.raw * 100)}%</td>
                    <td>{Math.round(p.calibrated * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {data.calibratedConfidence !== null && (
        <div className="ws-block">
          <div className="ws-confidence-final">
            <span className="ws-confidence-final__label">Confianza calibrada final</span>
            <span
              className="ws-confidence-final__value"
              style={{
                color: (data.calibratedConfidence ?? 0) >= 0.7 ? 'var(--uts-green)' : 'var(--lime-deep)',
              }}
            >
              {Math.round((data.calibratedConfidence ?? 0) * 100)}%
            </span>
            <span className="ws-confidence-final__hint">
              {(data.calibratedConfidence ?? 0) >= 0.8
                ? 'Alta confiabilidad'
                : (data.calibratedConfidence ?? 0) >= 0.6
                ? 'Confiabilidad moderada'
                : 'Confiabilidad baja — verificar fuentes'}
            </span>
          </div>
        </div>
      )}
    </WorkstreamSection>
  );
}

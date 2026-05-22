import type { WsaResult } from '@/types';
import { WorkstreamSection } from './WorkstreamSection';

interface WSASectionProps {
  data: WsaResult;
}

const RISK_LABELS: Record<string, string> = {
  low: 'Bajo',
  medium: 'Medio',
  high: 'Alto',
};

const RISK_COLORS: Record<string, string> = {
  low: 'badge--success',
  medium: 'badge--warning',
  high: 'badge--error',
};

export function WSASection({ data }: WSASectionProps) {
  return (
    <WorkstreamSection title="Calidad de fuentes (WS-A)" icon="search" status="active">

      {data.authorReputations.length > 0 && (
        <div className="ws-block">
          <h4>Reputación de autores</h4>
          <p className="ws-explain">
            El índice h mide simultáneamente productividad e impacto académico de un autor.
            Un h-index de 30 significa que el autor tiene al menos 30 publicaciones con ≥30 citas cada una.
          </p>
          <table className="ws-table">
            <thead>
              <tr>
                <th>Autor</th>
                <th>h-index</th>
                <th>Institución</th>
              </tr>
            </thead>
            <tbody>
              {data.authorReputations.map((a) => (
                <tr key={a.authorId}>
                  <td>{a.name}</td>
                  <td>
                    <span className={`badge badge--sm ${a.hIndex >= 30 ? 'badge--success' : a.hIndex >= 15 ? 'badge--warning' : 'badge--info'}`}>
                      {a.hIndex}
                    </span>
                  </td>
                  <td>{a.affiliation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.conflictsOfInterest.length > 0 && (
        <div className="ws-block">
          <h4>
            Conflictos de interés detectados{' '}
            <span className="badge badge--warning badge--sm">{data.conflictsOfInterest.length}</span>
          </h4>
          <p className="ws-explain">
            Un conflicto de interés ocurre cuando una fuente de financiamiento o afiliación corporativa
            puede sesgar los resultados publicados. Un ratio corporativo alto ({'>'} 0.6) indica que
            la mayoría del trabajo del autor está financiado por entidades con interés económico
            directo en los hallazgos.
          </p>
          <div className="ws-conflict-list">
            {data.conflictsOfInterest.map((c, i) => (
              <div key={i} className={`ws-conflict-card ws-conflict-card--${c.riskLevel}`}>
                <div className="ws-conflict-card__header">
                  <span className={`badge ${RISK_COLORS[c.riskLevel] ?? 'badge--info'}`}>
                    Riesgo {RISK_LABELS[c.riskLevel] ?? c.riskLevel}
                  </span>
                  <span className="ws-conflict-card__entity">{c.funderEntity}</span>
                </div>
                <p className="ws-conflict-card__reason">
                  {c.riskLevel === 'high'
                    ? `El ${Math.round(c.corporateRatio * 100)}% de la investigación de este autor está financiada por ${c.funderEntity}. Esto introduce un sesgo potencial de confirmación hacia resultados favorables al financiador.`
                    : c.riskLevel === 'medium'
                    ? `Aproximadamente el ${Math.round(c.corporateRatio * 100)}% de la financiación proviene de ${c.funderEntity}. Se recomienda corroborar los hallazgos con fuentes independientes.`
                    : `Existe una relación de financiamiento menor con ${c.funderEntity} (${Math.round(c.corporateRatio * 100)}%). Impacto considerado bajo.`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.externalValidations.length > 0 && (
        <div className="ws-block">
          <h4>Validaciones externas</h4>
          <p className="ws-explain">
            Contraste de los hallazgos clave contra bases de datos de verificación de hechos
            y repositorios científicos independientes.
          </p>
          <ul className="ws-list">
            {data.externalValidations.map((v, i) => (
              <li key={i}>
                <span className={`badge badge--sm ${
                  v.status === 'verified' ? 'badge--success'
                  : v.status === 'contradicted' ? 'badge--error'
                  : 'badge--info'
                }`}>
                  {v.status === 'verified' ? 'Verificado' : v.status === 'contradicted' ? 'Contradicho' : 'No encontrado'}
                </span>
                {' '}<strong>{v.summary}</strong>
                <span className="ws-source-tag">vía {v.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.retractionRecords.length > 0 && (
        <div className="ws-block ws-block--alert">
          <h4>
            ⚠ Artículos retractados en el corpus
            <span className="badge badge--error badge--sm" style={{ marginLeft: 8 }}>
              {data.retractionRecords.length}
            </span>
          </h4>
          <p className="ws-explain ws-explain--warn">
            Se detectaron publicaciones previamente usadas como fuente que han sido
            retractadas por sus revistas. Una retractación invalida los resultados originales.
            Los hallazgos basados en estas fuentes deben descartarse o revalidarse.
          </p>
          <div className="ws-retraction-list">
            {data.retractionRecords.map((r, i) => (
              <div key={i} className="ws-retraction-card">
                <div className="ws-retraction-card__title">{r.title ?? r.doi}</div>
                <div className="ws-retraction-card__meta">
                  <span>DOI: <code>{r.doi}</code></span>
                  {r.retractionDate && <span>Fecha de retractación: {r.retractionDate}</span>}
                </div>
                {r.reason && (
                  <div className="ws-retraction-card__reason">
                    <strong>Motivo:</strong> {r.reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.reproducibilityScores.length > 0 && (
        <div className="ws-block">
          <h4>Reproducibilidad</h4>
          <p className="ws-explain">
            Indica qué tan probable es que los resultados de una fuente puedan ser
            replicados por terceros. Se considera aceptable ≥ 70%.
          </p>
          <div className="ws-meter-list">
            {data.reproducibilityScores.map((s, i) => (
              <div key={i} className="ws-meter">
                <span className="ws-meter__label">{s.sourceId}</span>
                <div className="ws-meter__bar">
                  <div
                    className="ws-meter__fill"
                    style={{
                      width: `${Math.round(s.score * 100)}%`,
                      background: s.score >= 0.7 ? 'var(--lime-deep)' : 'var(--st-fail)',
                    }}
                  />
                </div>
                <span className="ws-meter__value">{Math.round(s.score * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </WorkstreamSection>
  );
}

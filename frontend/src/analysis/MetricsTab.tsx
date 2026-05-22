import type { AnalysisMetrics, WsbResult } from '@/types';
import { StateBlock } from '@/components';
import { getBranchColor, getBranchLabel } from '@/graph/graphUtils';

interface MetricsTabProps {
  metrics: AnalysisMetrics | null;
  loading: boolean;
  error: string | null;
  wsB?: WsbResult | null;
}

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

export function MetricsTab({ metrics, loading, error, wsB }: MetricsTabProps) {
  if (loading) {
    return <StateBlock kind="loading" title="Recopilando métricas de campo" />;
  }
  if (error) {
    return (
      <StateBlock
        kind="error"
        title="No se pudieron cargar las métricas"
        hint={error}
      />
    );
  }
  if (!metrics && !wsB) {
    return (
      <StateBlock
        kind="empty"
        glyph="SIN MEDICIONES"
        title="Aún no hay métricas"
        hint="Las métricas se calculan al completarse la investigación."
      />
    );
  }

  const maxLatency = Math.max(
    1,
    ...(metrics?.providerMetrics.map((p) => p.avgLatencyMs) ?? []),
  );

  return (
    <div className="metrics">
      {metrics && (
        <>
          <div className="metrics__cards">
            <div className="metric-card">
              <div className="metric-card__label">Confianza global</div>
              <div className="metric-card__value">
                {pct(metrics.confidenceScore)}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Fuentes consultadas</div>
              <div className="metric-card__value">{metrics.totalSources}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Hallazgos</div>
              <div className="metric-card__value">{metrics.totalFindings}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Ramas evaluadas</div>
              <div className="metric-card__value">
                {metrics.branchKpis.length}
              </div>
            </div>
          </div>

          <div>
            <h3 className="atlas-section-title">
              KPIs por rama <small>// cobertura · precisión · latencia</small>
            </h3>
            <table className="dtable">
              <thead>
                <tr>
                  <th>Rama</th>
                  <th>Cobertura</th>
                  <th>Precisión</th>
                  <th>Latencia</th>
                </tr>
              </thead>
              <tbody>
                {metrics.branchKpis.map((kpi) => (
                  <tr key={kpi.branchType}>
                    <td>
                      <span
                        className="dtable__swatch"
                        style={{ background: getBranchColor(kpi.branchType) }}
                      />
                      {getBranchLabel(kpi.branchType)}
                    </td>
                    <td>{pct(kpi.coverageKpi)}</td>
                    <td>{pct(kpi.precisionKpi)}</td>
                    <td>{kpi.latencyMsKpi} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="atlas-section-title">
              Proveedores MCP <small>// latencia · error · reintentos</small>
            </h3>
            <table className="dtable">
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Latencia media</th>
                  <th>Tasa de error</th>
                  <th>Tasa de reintento</th>
                </tr>
              </thead>
              <tbody>
                {metrics.providerMetrics.map((p) => (
                  <tr key={p.providerName}>
                    <td>{p.providerName}</td>
                    <td>
                      {p.avgLatencyMs} ms
                      <span
                        className="dtable__bar"
                        style={{
                          width: `${(p.avgLatencyMs / maxLatency) * 90}px`,
                        }}
                      />
                    </td>
                    <td>{pct(p.errorRate)}</td>
                    <td>{pct(p.retryRate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {metrics.confidenceCalibration.length > 0 && (
            <div>
              <h3 className="atlas-section-title">
                Calibración de confianza{' '}
                <small>// predicho · observado · factor de corrección</small>
              </h3>
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Bucket</th>
                    <th>Predicho</th>
                    <th>Observado</th>
                    <th>Muestras</th>
                    <th>Factor</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.confidenceCalibration.map((b) => (
                    <tr key={b.bucket}>
                      <td>{b.bucket}</td>
                      <td>{pct(b.predicted)}</td>
                      <td>{pct(b.observed)}</td>
                      <td>{b.samples}</td>
                      <td>
                        <span
                          className={
                            b.factor < 1
                              ? 'dtable__delta dtable__delta--down'
                              : 'dtable__delta dtable__delta--up'
                          }
                        >
                          ×{b.factor.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* WS-B Data Intelligence — movido desde el informe */}
      {wsB && (
        <div className="metrics__wsb">
          <h3 className="atlas-section-title">
            Inteligencia de datos (WS-B){' '}
            <small>// búsqueda híbrida · deduplicación · autenticidad</small>
          </h3>

          {wsB.hybridSearchStats && Object.keys(wsB.hybridSearchStats).length > 0 && (
            <div className="metrics__cards" style={{ marginBottom: 20 }}>
              {Object.entries(wsB.hybridSearchStats).map(([k, v]) => (
                <div key={k} className="metric-card">
                  <div className="metric-card__label">{k.replace(/_/g, ' ')}</div>
                  <div className="metric-card__value" style={{ fontSize: 28 }}>
                    {v as number}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginBottom: 20 }}>
            <div className="ws-meter">
              <span className="ws-meter__label">
                Tasa de deduplicación — {Math.round(wsB.dedupRate * 100)}% de fuentes duplicadas eliminadas
              </span>
              <div className="ws-meter__bar">
                <div className="ws-meter__fill" style={{ width: `${Math.round(wsB.dedupRate * 100)}%` }} />
              </div>
              <span className="ws-meter__value">{Math.round(wsB.dedupRate * 100)}%</span>
            </div>
          </div>

          {wsB.authenticitySignals.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h4 className="atlas-section-title" style={{ fontSize: 13 }}>
                Señales de autenticidad <small>// probabilidad de contenido generado por IA</small>
              </h4>
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Fuente</th>
                    <th>Veredicto</th>
                    <th>Prob. IA</th>
                    <th>Prob. Humano</th>
                  </tr>
                </thead>
                <tbody>
                  {wsB.authenticitySignals.map((s, i) => (
                    <tr key={i}>
                      <td>{s.sourceId}</td>
                      <td>
                        <span className={`badge badge--sm ${s.verdict === 'likely_ai' ? 'badge--warning' : 'badge--success'}`}>
                          {s.verdict === 'likely_ai' ? 'Probable IA' : 'Probable humano'}
                        </span>
                      </td>
                      <td>{Math.round(s.aiProbability * 100)}%</td>
                      <td>{Math.round(s.humanProbability * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {wsB.consensusDisputes.length > 0 && (
            <div>
              <h4 className="atlas-section-title" style={{ fontSize: 13 }}>
                Consenso y disputas entre fuentes
              </h4>
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Tema</th>
                    <th>Estado</th>
                    <th>Fuentes</th>
                    <th>Confianza</th>
                  </tr>
                </thead>
                <tbody>
                  {wsB.consensusDisputes.map((c, i) => (
                    <tr key={i}>
                      <td>{c.topic}</td>
                      <td>
                        <span className={`badge badge--sm ${c.agreement ? 'badge--success' : 'badge--error'}`}>
                          {c.agreement ? 'Consenso' : 'Disputa'}
                        </span>
                      </td>
                      <td>{c.sourceCount}</td>
                      <td>{Math.round(c.confidence * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import type { AnalysisMetrics } from '@/types';
import { StateBlock } from '@/components';
import { getBranchColor, getBranchLabel } from '@/graph/graphUtils';

interface MetricsTabProps {
  metrics: AnalysisMetrics | null;
  loading: boolean;
  error: string | null;
}

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

export function MetricsTab({ metrics, loading, error }: MetricsTabProps) {
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
  if (!metrics) {
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
    ...metrics.providerMetrics.map((p) => p.avgLatencyMs),
  );

  return (
    <div className="metrics">
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
    </div>
  );
}

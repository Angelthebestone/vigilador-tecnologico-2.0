import { useEffect, useState } from 'react';
import type { AnalysisMetrics, Recommendation, BranchType } from '@/types';
import { getMetrics, getReport } from '@/api';
import { useStore } from '@/state/useStore';
import { AnalysisPanel } from './AnalysisPanel';
import { MetricsTab } from './MetricsTab';
import { RecommendationsTab } from './RecommendationsTab';
import { GraphTab } from './GraphTab';

interface AnalysisViewProps {
  historyBar: React.ReactNode;
}

/**
 * El contenido se remonta vía `key={sessionId}` cuando cambia la sesión,
 * de modo que el estado arranca limpio sin reset síncrono en el efecto.
 */
function AnalysisContent({ sessionId }: { sessionId: string | null }) {
  const [metrics, setMetrics] = useState<AnalysisMetrics | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [mLoading, setMLoading] = useState(Boolean(sessionId));
  const [mError, setMError] = useState<string | null>(null);
  const [rLoading, setRLoading] = useState(Boolean(sessionId));
  const [rError, setRError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    let active = true;

    getMetrics(sessionId)
      .then((res) => {
        if (!active) return;
        setMetrics({
          branchKpis: [] as {
            branchType: BranchType;
            coverageKpi: number;
            precisionKpi: number;
            latencyMsKpi: number;
            costKpi: number;
          }[],
          providerMetrics: res.providers.map((p) => ({
            providerName: p.name,
            avgLatencyMs: p.avgLatencyMs,
            errorRate: p.errorRate,
            retryRate: p.retryRate,
            latencyBuckets: {},
          })),
          confidenceScore: 0,
          totalSources: 0,
          totalFindings: 0,
        });
      })
      .catch((err: unknown) => {
        if (active)
          setMError(err instanceof Error ? err.message : 'Error desconocido');
      })
      .finally(() => active && setMLoading(false));

    getReport(sessionId)
      .then((report) => {
        if (active) setRecommendations(report.recommendations ?? []);
      })
      .catch((err: unknown) => {
        if (active)
          setRError(err instanceof Error ? err.message : 'Error desconocido');
      })
      .finally(() => active && setRLoading(false));

    return () => {
      active = false;
    };
  }, [sessionId]);

  return (
    <AnalysisPanel
      graph={<GraphTab key={sessionId ?? 'none'} sessionId={sessionId} />}
      metrics={
        <MetricsTab metrics={metrics} loading={mLoading} error={mError} />
      }
      recommendations={
        <RecommendationsTab
          recommendations={recommendations}
          loading={rLoading}
          error={rError}
        />
      }
    />
  );
}

export function AnalysisView({ historyBar }: AnalysisViewProps) {
  const sessionId = useStore((s) => s.sessionId);

  return (
    <div className="atlas-body">
      {historyBar}
      <div className="atlas-plate">
        <AnalysisContent key={sessionId ?? 'none'} sessionId={sessionId} />
      </div>
    </div>
  );
}

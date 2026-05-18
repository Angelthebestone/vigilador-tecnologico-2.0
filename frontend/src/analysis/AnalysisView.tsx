import { useEffect } from 'react';
import { useStore } from '@/state/useStore';
import { useAnalysisStore } from '@/state/analysisStore';
import { AnalysisPanel } from './AnalysisPanel';
import { MetricsTab } from './MetricsTab';
import { RecommendationsTab } from './RecommendationsTab';
import { GraphTab } from './GraphTab';

interface AnalysisViewProps {
  historyBar: React.ReactNode;
}

function AnalysisContent({ sessionId }: { sessionId: string | null }) {
  const metrics = useAnalysisStore((s) => s.metrics);
  const recommendations = useAnalysisStore((s) => s.recommendations);
  const metricsLoading = useAnalysisStore((s) => s.metricsLoading);
  const recommendationsLoading = useAnalysisStore((s) => s.recommendationsLoading);
  const metricsError = useAnalysisStore((s) => s.metricsError);
  const recommendationsError = useAnalysisStore((s) => s.recommendationsError);
  const fetchMetrics = useAnalysisStore((s) => s.fetchMetrics);
  const fetchRecommendations = useAnalysisStore((s) => s.fetchRecommendations);

  useEffect(() => {
    if (!sessionId) return;
    fetchMetrics(sessionId);
    fetchRecommendations(sessionId);
  }, [sessionId, fetchMetrics, fetchRecommendations]);

  return (
    <AnalysisPanel
      graph={<GraphTab key={sessionId ?? 'none'} sessionId={sessionId} />}
      metrics={
        <MetricsTab metrics={metrics} loading={metricsLoading} error={metricsError} />
      }
      recommendations={
        <RecommendationsTab
          recommendations={recommendations}
          loading={recommendationsLoading}
          error={recommendationsError}
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

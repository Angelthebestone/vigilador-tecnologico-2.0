import { create } from 'zustand';
import type { AnalysisMetrics, Recommendation } from '@/types';
import { getMetrics, getReport } from '@/api';

interface AnalysisStore {
  metrics: AnalysisMetrics | null;
  recommendations: Recommendation[];
  metricsLoading: boolean;
  recommendationsLoading: boolean;
  metricsError: string | null;
  recommendationsError: string | null;
  fetchMetrics: (sessionId: string) => Promise<void>;
  fetchRecommendations: (sessionId: string) => Promise<void>;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisStore>()((set) => ({
  metrics: null,
  recommendations: [],
  metricsLoading: false,
  recommendationsLoading: false,
  metricsError: null,
  recommendationsError: null,

  fetchMetrics: async (sessionId) => {
    set({ metricsLoading: true, metricsError: null });
    try {
      const res = await getMetrics(sessionId);
      set({
        metrics: {
          branchKpis: [],
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
        },
        metricsLoading: false,
      });
    } catch (err) {
      set({
        metricsError: err instanceof Error ? err.message : 'Error desconocido',
        metricsLoading: false,
      });
    }
  },

  fetchRecommendations: async (sessionId) => {
    set({ recommendationsLoading: true, recommendationsError: null });
    try {
      const report = await getReport(sessionId);
      set({
        recommendations: report.recommendations ?? [],
        recommendationsLoading: false,
      });
    } catch (err) {
      set({
        recommendationsError:
          err instanceof Error ? err.message : 'Error desconocido',
        recommendationsLoading: false,
      });
    }
  },

  reset: () =>
    set({
      metrics: null,
      recommendations: [],
      metricsLoading: false,
      recommendationsLoading: false,
      metricsError: null,
      recommendationsError: null,
    }),
}));

import { create } from 'zustand';
import type { AnalysisMetrics, Recommendation } from '@/types';
import { getMetrics, getReport, getBranchEvaluation } from '@/api';

interface AnalysisStore {
  metrics: AnalysisMetrics | null;
  recommendations: Recommendation[];
  metricsLoading: boolean;
  recommendationsLoading: boolean;
  metricsError: string | null;
  recommendationsError: string | null;
  fetchMetrics: (sessionId: string) => Promise<void>;
  fetchRecommendations: (sessionId: string) => Promise<void>;
  setBranchKpis: (sessionId: string, kpis: AnalysisMetrics['branchKpis']) => void;
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
      const [providersRes, evaluationRes] = await Promise.all([
        getMetrics(sessionId),
        getBranchEvaluation(sessionId).catch(() => null),
      ]);
      const evaluationKpis =
        evaluationRes?.byBranch?.map((e) => ({
          branchType: e.branchType as AnalysisMetrics['branchKpis'][number]['branchType'],
          coverageKpi: e.coverageKpi,
          precisionKpi: e.precisionKpi,
          latencyMsKpi: e.latencyMsKpi,
        })) ?? [];
      const raw = providersRes as typeof providersRes & {
        branchKpis?: Array<{ branchType: string; coverageKpi: number; precisionKpi: number; latencyMsKpi: number }>;
        confidenceScore?: number;
        totalSources?: number;
        totalFindings?: number;
        confidenceCalibration?: Array<{ bucket: string; predicted: number; observed: number; samples: number; factor: number }>;
      };
      set({
        metrics: {
          branchKpis: raw.branchKpis?.length ? raw.branchKpis : evaluationKpis,
          providerMetrics: providersRes.providers.map((p) => ({
            providerName: p.name,
            avgLatencyMs: p.avgLatencyMs,
            errorRate: p.errorRate,
            retryRate: p.retryRate,
            latencyBuckets: {},
          })),
          confidenceScore: raw.confidenceScore ?? 0,
          totalSources: raw.totalSources ?? 0,
          totalFindings: raw.totalFindings ?? 0,
          confidenceCalibration: raw.confidenceCalibration ?? [],
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

  setBranchKpis: (sessionId, kpis) => {
    set((state) => {
      if (!state.metrics) return {};
      return { metrics: { ...state.metrics, branchKpis: kpis } };
    });
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

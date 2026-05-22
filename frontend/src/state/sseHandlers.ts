import { getReport } from '@/api';
import { useAnalysisStore } from './analysisStore';
import { useStore } from './useStore';
import { useChatStore } from './chatStore';
import { useAgentsStore } from './agentsStore';
import { useHistoryStore } from './historyStore';
import { useConfigStore } from './configStore';
import type {
  ResearchPlan,
  FinalReport,
  ThinkingStep,
  BranchType,
  ReplanSignal,
  SessionEvaluation,
} from '@/types';

interface SessionStartedData {
  sessionId: string;
  userQuery: string;
}

interface ClarificationRequestedData {
  questions: Array<{ id: string; text: string }>;
}

interface PlanGeneratedData {
  plan: ResearchPlan;
}

interface BranchEventData {
  branch: BranchType;
}

interface BranchProgressData {
  branch: BranchType;
  iteration: ThinkingStep;
}

interface ReportGeneratedData {
  report: FinalReport;
  evaluation?: SessionEvaluation;
}

interface GraphEventData {
  sessionId: string;
}

export function createSSEHandlers(): Record<string, (data: unknown) => void> {
  const store = useStore.getState();
  const chatStore = useChatStore.getState();
  const agentsStore = useAgentsStore.getState();

  return {
    SessionStarted: (data) => {
      const d = data as SessionStartedData;
      // Solo poblar sessionId/userQuery si todavía no están seteados; nunca
      // reescribir cuando ya estamos en EXECUTING tras el approve, porque
      // setSession resetea sessionStatus a 'DRAFT' y rompe el SSE en marcha.
      const current = useStore.getState();
      if (!current.sessionId) {
        store.setSession(d.sessionId, d.userQuery);
      }
      chatStore.addMessage({
        type: 'system',
        role: 'assistant',
        content: `Investigación iniciada: "${d.userQuery}"`,
        metadata: { sessionId: d.sessionId },
      });
    },

    ClarificationRequested: (data) => {
      const d = data as ClarificationRequestedData;
      chatStore.addClarification(d.questions);
    },

    PlanGenerated: (data) => {
      const d = data as PlanGeneratedData;
      store.setPlan(d.plan);
      chatStore.addMessage({
        type: 'plan',
        role: 'assistant',
        content: 'Plan de investigación generado.',
        metadata: { plan: d.plan },
      });
    },

    BranchStarted: (data) => {
      const d = data as BranchEventData;
      agentsStore.setAgentStatus(d.branch, 'running');
    },

    BranchProgress: (data) => {
      const d = data as BranchProgressData;
      agentsStore.addIteration(d.branch, d.iteration);
    },

    ReplanTriggered: (data) => {
      agentsStore.addReplanSignal(data as ReplanSignal);
    },

    BranchCompleted: (data) => {
      const d = data as BranchEventData;
      agentsStore.setAgentStatus(d.branch, 'completed');
    },

    BranchFailed: (data) => {
      const d = data as BranchEventData;
      agentsStore.setAgentStatus(d.branch, 'failed');
    },

    AllBranchesCompleted: () => {
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Todas las ramas de investigación han completado su ejecución.',
      });
    },

    FusionStarted: () => {
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Iniciando fusión de resultados...',
      });
    },

    FusionProgress: () => {
      // no UI action required
    },

    ReportGenerated: async (data) => {
      const d = data as ReportGeneratedData;
      const sessionId = useStore.getState().sessionId;
      if (!sessionId) return;
      try {
        const report = await getReport(sessionId);
        // Spec 008 T037 — attach evaluation from SSE payload when available
        if (d.evaluation && !report.evaluation) {
          (report as FinalReport).evaluation = d.evaluation;
        }
        useStore.getState().setReport(report);
        useStore.getState().setSessionStatus('COMPLETED');
        const userQuery = useStore.getState().userQuery;
        useHistoryStore.getState().addSession(sessionId, userQuery, 'COMPLETED');
        useChatStore.getState().addMessage({
          type: 'report',
          role: 'assistant',
          content: 'Informe final generado.',
          metadata: { report, reportId: report.sessionId },
        });
        useChatStore.getState().addMessage({
          type: 'event',
          role: 'assistant',
          content:
            'Investigación completada. Puede continuar preguntando sobre los hallazgos sin lanzar una nueva investigación.',
        });
      } catch (err) {
        // If getReport fails, fall back to event data
        useStore.getState().setReport(d.report);
        useStore.getState().setSessionStatus('COMPLETED');
      }
    },

    ReportVariantsGenerated: (data) => {
      const d = data as { types?: string[] };
      if (Array.isArray(d.types) && d.types.length > 0) {
        useStore.getState().setReportVariants(d.types);
      }
    },

    PlanApproved: (data) => {
      useStore.getState().setSessionStatus('APPROVED');
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Plan de investigación aprobado.',
      });
    },

    EvaluationComputed: (data) => {
      const d = data as {
        sessionId?: string;
        evaluations?: Array<{ branchType: string; coverageKpi: number; precisionKpi: number; latencyMsKpi: number }>;
        byBranch?: Array<{ branchType: string; coverageKpi: number; precisionKpi: number; latencyMsKpi: number }>;
      };
      const kpis = d.evaluations ?? d.byBranch;
      if (kpis && kpis.length > 0) {
        useAnalysisStore.getState().setBranchKpis(
          d.sessionId ?? '',
          kpis.map((e) => ({
            branchType: e.branchType as import('@/types').BranchType,
            coverageKpi: e.coverageKpi,
            precisionKpi: e.precisionKpi,
            latencyMsKpi: e.latencyMsKpi,
          })),
        );
      }
      // Spec 008 T037 — refresh config store so WorkstreamIndicator stays in sync
      useConfigStore.getState().fetchWorkstreams();
    },

    GraphBuildingStarted: (data) => {
      const d = data as GraphEventData;
      const sessionId = d.sessionId;
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Construyendo grafo de conocimiento...',
        metadata: { sessionId },
      });
    },

    GraphAnalyticsComputed: (data) => {
      const d = data as GraphEventData;
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Analíticas de grafo disponibles.',
        metadata: { sessionId: d.sessionId },
      });
    },
  };
}

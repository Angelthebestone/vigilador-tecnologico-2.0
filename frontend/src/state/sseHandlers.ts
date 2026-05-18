import { useStore } from './useStore';
import { useChatStore } from './chatStore';
import { useAgentsStore } from './agentsStore';
import type {
  ResearchPlan,
  FinalReport,
  ThinkingStep,
  BranchType,
  ReplanSignal,
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
      store.setSession(d.sessionId, d.userQuery);
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

    ReportGenerated: (data) => {
      const d = data as ReportGeneratedData;
      useStore.getState().setReport(d.report);
      useStore.getState().setSessionStatus('COMPLETED');
      useChatStore.getState().addMessage({
        type: 'report',
        role: 'assistant',
        content: 'Informe final generado.',
        metadata: { report: d.report, reportId: d.report.sessionId },
      });
      useChatStore.getState().addMessage({
        type: 'event',
        role: 'assistant',
        content:
          'Investigación completada. Puede continuar preguntando sobre los hallazgos sin lanzar una nueva investigación.',
      });
    },

    ReportVariantsGenerated: (data) => {
      const d = data as { types?: string[] };
      if (Array.isArray(d.types) && d.types.length > 0) {
        useStore.getState().setReportVariants(d.types);
      }
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

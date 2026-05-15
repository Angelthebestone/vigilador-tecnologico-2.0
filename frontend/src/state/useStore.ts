import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  SessionStatus,
  BranchAgent,
  ResearchPlan,
  FinalReport,
  GraphData,
  SSEConnectionStatus,
  ThinkingStep,
  BranchAgentStatus,
} from '@/types';

export interface SessionSlice {
  sessionId: string | null;
  userQuery: string;
  sessionStatus: SessionStatus | null;
  plan: ResearchPlan | null;
  report: FinalReport | null;
  setSession: (id: string, query: string) => void;
  setSessionStatus: (status: SessionStatus) => void;
  setPlan: (plan: ResearchPlan) => void;
  setReport: (report: FinalReport) => void;
  clearSession: () => void;
}

export interface AgentSlice {
  agents: Record<string, BranchAgent>;
  updateAgent: (branchType: string, updates: Partial<BranchAgent>) => void;
  addAgentIteration: (branchType: string, iteration: ThinkingStep) => void;
  setAgentStatus: (branchType: string, status: BranchAgentStatus) => void;
  resetAgents: () => void;
}

export interface GraphSlice {
  graphData: GraphData | null;
  selectedNodeId: string | null;
  setGraphData: (data: GraphData) => void;
  setSelectedNode: (nodeId: string | null) => void;
}

export interface SSESlice {
  sseStatus: SSEConnectionStatus;
  setSseStatus: (status: SSEConnectionStatus) => void;
}

export type AppStore = SessionSlice & AgentSlice & GraphSlice & SSESlice;

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      sessionId: null,
      userQuery: '',
      sessionStatus: null,
      plan: null,
      report: null,
      setSession: (id, query) => set({ sessionId: id, userQuery: query, sessionStatus: 'DRAFT' }),
      setSessionStatus: (status) => set({ sessionStatus: status }),
      setPlan: (plan) => set({ plan }),
      setReport: (report) => set({ report }),
      clearSession: () =>
        set({
          sessionId: null,
          userQuery: '',
          sessionStatus: null,
          plan: null,
          report: null,
          graphData: null,
          selectedNodeId: null,
        }),

      agents: {},
      updateAgent: (branchType, updates) =>
        set((state) => ({
          agents: { ...state.agents, [branchType]: { ...state.agents[branchType], ...updates } as BranchAgent },
        })),
      addAgentIteration: (branchType, iteration) =>
        set((state) => {
          const agent = state.agents[branchType];
          if (!agent) return state;
          return {
            agents: {
              ...state.agents,
              [branchType]: {
                ...agent,
                iterations: [...agent.iterations, iteration],
                currentIteration: agent.currentIteration + 1,
              },
            },
          };
        }),
      setAgentStatus: (branchType, status) =>
        set((state) => {
          const agent = state.agents[branchType];
          if (!agent) return state;
          return { agents: { ...state.agents, [branchType]: { ...agent, status } } };
        }),
      resetAgents: () => set({ agents: {} }),

      graphData: null,
      selectedNodeId: null,
      setGraphData: (data) => set({ graphData: data }),
      setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),

      sseStatus: 'disconnected',
      setSseStatus: (status) => set({ sseStatus: status }),
    }),
    {
      name: 'vigilador-session',
      partialize: (state) => ({
        sessionId: state.sessionId,
        userQuery: state.userQuery,
      }),
    }
  )
);

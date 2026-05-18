import { create } from 'zustand';
import type {
  BranchAgent,
  ThinkingStep,
  BranchAgentStatus,
  BranchType,
  ReplanSignal,
} from '@/types';

const createAgent = (branchType: BranchType): BranchAgent => ({
  branchType,
  status: 'waiting',
  currentIteration: 0,
  totalIterations: 0,
  iterations: [],
  confidence: 0,
});

interface AgentsStore {
  agents: Record<string, BranchAgent>;
  selectedAgentIndex: number;
  replanSignals: ReplanSignal[];
  setSelectedAgent: (index: number) => void;
  updateAgent: (branchType: string, updates: Partial<BranchAgent>) => void;
  addIteration: (branchType: string, step: ThinkingStep) => void;
  addReplanSignal: (signal: ReplanSignal) => void;
  setAgentStatus: (branchType: string, status: BranchAgentStatus) => void;
  resetAgents: () => void;
  initializeAgents: (branchTypes: readonly BranchType[]) => void;
}

export const useAgentsStore = create<AgentsStore>()((set) => ({
  agents: {},
  selectedAgentIndex: 0,
  replanSignals: [],

  setSelectedAgent: (index) => set({ selectedAgentIndex: index }),

  updateAgent: (branchType, updates) =>
    set((state) => ({
      agents: { ...state.agents, [branchType]: { ...state.agents[branchType], ...updates } as BranchAgent },
    })),

  addIteration: (branchType, step) =>
    set((state) => {
      const agent = state.agents[branchType];
      if (!agent) return state;
      return {
        agents: {
          ...state.agents,
          [branchType]: {
            ...agent,
            iterations: [...agent.iterations, step],
            currentIteration: agent.currentIteration + 1,
          },
        },
      };
    }),

  addReplanSignal: (signal) =>
    set((state) => ({ replanSignals: [...state.replanSignals, signal] })),

  setAgentStatus: (branchType, status) =>
    set((state) => {
      const agent = state.agents[branchType];
      if (!agent) return state;
      return { agents: { ...state.agents, [branchType]: { ...agent, status } } };
    }),

  resetAgents: () => set({ agents: {}, selectedAgentIndex: 0, replanSignals: [] }),

  initializeAgents: (branchTypes) =>
    set((state) => {
      const agents = { ...state.agents };
      for (const bt of branchTypes) {
        if (!agents[bt]) {
          agents[bt] = createAgent(bt);
        }
      }
      return { agents };
    }),
}));

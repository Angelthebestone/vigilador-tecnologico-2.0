import { useStore } from './useStore';
import { useChatStore } from './chatStore';
import { useConfigStore } from './configStore';
import type {
  BranchAgent,
  GraphData,
  FinalReport,
  ResearchPlan,
  SessionStatus,
  ChatMessage,
  WorkstreamConfig,
  PromptTemplate,
  WorkstreamHealth,
} from '@/types';

export function useChatMessages(): ChatMessage[] {
  return useChatStore((s) => s.messages);
}

export function useActiveSession() {
  return useStore((s) => ({
    id: s.sessionId,
    query: s.userQuery,
    status: s.sessionStatus,
  }));
}

export function useAgents(): Record<string, BranchAgent> {
  return useStore((s) => s.agents);
}

export function useGraph() {
  return useStore((s) => ({
    data: s.graphData,
    selectedNodeId: s.selectedNodeId,
    setSelectedNode: s.setSelectedNode,
  }));
}

export function useReport(): FinalReport | null {
  return useStore((s) => s.report);
}

export function useSessionStatus() {
  return useStore((s) => ({
    sessionId: s.sessionId,
    sessionStatus: s.sessionStatus,
    plan: s.plan,
  }));
}

export function useSseStatus() {
  return useStore((s) => s.sseStatus);
}

export type { GraphData, FinalReport, ResearchPlan, SessionStatus };

import { apiGet, apiPost } from './client';
import type { ResearchPlan, FinalReport, GraphData, Source } from '@/types';

export async function startResearch(
  query: string,
  scope?: Record<string, string>,
): Promise<{
  sessionId: string;
  status: string;
  questions: Array<{ id: string; text: string }>;
}> {
  return apiPost('/research/start', { query, scope });
}

export async function clarifySession(
  sessionId: string,
  answers: Record<string, string>,
): Promise<{
  sessionId: string;
  status: string;
  requiresApproval: boolean;
  plan: ResearchPlan;
}> {
  return apiPost(`/research/${sessionId}/clarify`, { answers });
}

export async function getPlan(
  sessionId: string,
): Promise<{ sessionId: string; plan: ResearchPlan }> {
  return apiGet(`/research/${sessionId}/plan`);
}

export async function approvePlan(
  sessionId: string,
): Promise<{ sessionId: string; status: string; message: string }> {
  return apiPost(`/research/${sessionId}/approve`);
}

export async function getReport(sessionId: string): Promise<FinalReport> {
  return apiGet(`/research/${sessionId}/report`);
}

export async function getSources(
  sessionId: string,
): Promise<{ sessionId: string; total: number; items: Source[] }> {
  return apiGet(`/research/${sessionId}/sources`);
}

export async function getGraph(sessionId: string): Promise<GraphData> {
  return apiGet(`/research/${sessionId}/graph`);
}

export async function getGraphAnalytics(sessionId: string): Promise<unknown> {
  return apiGet(`/research/${sessionId}/graph/analytics`);
}

export async function searchGraph(
  sessionId: string,
  query: string,
): Promise<{
  items: Array<{ nodeId: string; label: string; score: number }>;
}> {
  return apiGet(
    `/research/${sessionId}/graph/search?query=${encodeURIComponent(query)}`,
  );
}

export async function getGraphPath(
  sessionId: string,
  sourceNodeId: string,
  targetNodeId: string,
): Promise<{ nodeIds: string[]; edgeIds: string[]; totalCost: number }> {
  return apiGet(
    `/research/${sessionId}/graph/path?sourceNodeId=${encodeURIComponent(sourceNodeId)}&targetNodeId=${encodeURIComponent(targetNodeId)}`,
  );
}

export async function getMetrics(
  sessionId: string,
): Promise<{
  sessionId: string;
  providers: Array<{
    name: string;
    avgLatencyMs: number;
    errorRate: number;
    retryRate: number;
  }>;
}> {
  return apiGet(`/research/${sessionId}/providers`);
}

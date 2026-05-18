import { apiGet, apiPost, apiDel, apiUpload, apiPatch, API_BASE } from './client';
import type {
  ResearchPlan,
  FinalReport,
  GraphData,
  Source,
  FollowUpAnswer,
  SessionTimelineEntry,
  SourceScoreResult,
} from '@/types';

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
  return apiPost(`/research/${sessionId}/approve`, { approved: true });
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

export async function getBranchEvaluation(
  sessionId: string,
): Promise<{
  sessionId: string;
  byBranch: Array<{
    branchType: string;
    coverageKpi: number;
    precisionKpi: number;
    latencyMsKpi: number;
    costKpi: number;
  }>;
}> {
  return apiGet(`/research/${sessionId}/evaluation`);
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

export async function deleteSession(
  sessionId: string,
): Promise<{ status: string; sessionId: string }> {
  return apiDel(`/research/${sessionId}`);
}

export async function uploadDocument(
  file: File,
): Promise<{ markdown: string; format: string; filename: string }> {
  return apiUpload('/upload/document', file);
}

/**
 * Conversación continua: pregunta de seguimiento sobre una sesión ya completada.
 * El backend responde directamente desde el grafo existente, o pide permiso
 * para lanzar una búsqueda suplementaria (`requiresPermission`).
 */
export async function askFollowUp(
  sessionId: string,
  query: string,
): Promise<FollowUpAnswer> {
  return apiPost(`/sessions/${sessionId}/ask`, { query });
}

export async function endConversation(
  sessionId: string,
): Promise<{ status: string }> {
  return apiDel(`/sessions/${sessionId}/conversation`);
}

/** Memoria cross-sesión: línea de tiempo de sesiones previas. */
export async function getSessionTimeline(): Promise<{
  sessions: SessionTimelineEntry[];
}> {
  return apiGet('/sessions/timeline');
}

/** URL directa de descarga de un reporte exportado (MD o HTML). */
export function reportExportUrl(
  reportId: string,
  format: 'md' | 'html',
): string {
  return `${API_BASE}/reports/${encodeURIComponent(reportId)}/export?format=${format}`;
}

/** Trust scoring: ajuste manual de la confianza de una fuente. */
export async function adjustSourceScore(
  sourceId: string,
  delta: number,
  reason: string,
): Promise<SourceScoreResult> {
  return apiPatch(`/sources/${encodeURIComponent(sourceId)}/score`, {
    delta,
    reason,
  });
}

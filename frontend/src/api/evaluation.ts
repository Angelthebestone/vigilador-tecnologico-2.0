import { apiGet, apiPatch, apiPost, apiPut } from './client';
import type {
  WorkstreamConfig,
  WorkstreamHealth,
  PromptTemplate,
  PromptKind,
  SessionEvaluation,
} from '@/types';

export async function getWorkstreamConfig(): Promise<WorkstreamConfig> {
  return apiGet('/config/workstreams');
}

export async function patchWorkstreamConfig(
  data: Partial<WorkstreamConfig>,
): Promise<WorkstreamConfig & { appliesTo: string }> {
  return apiPatch('/config/workstreams', data);
}

export async function getWorkstreamHealth(): Promise<WorkstreamHealth> {
  return apiGet('/config/workstreams/health');
}

export async function getPromptList(): Promise<{ templates: PromptTemplate[] }> {
  return apiGet('/config/prompts');
}

export async function getPrompt(
  name: string,
  kind: PromptKind = 'system',
): Promise<PromptTemplate & { content: string; defaultContent: string; kind: PromptKind }> {
  return apiGet(
    `/config/prompts/${encodeURIComponent(name)}?kind=${encodeURIComponent(kind)}`,
  );
}

export async function putPrompt(
  name: string,
  content: string,
  kind: PromptKind = 'system',
): Promise<{ name: string; modified: boolean; size: number; kind: PromptKind }> {
  return apiPut(
    `/config/prompts/${encodeURIComponent(name)}?kind=${encodeURIComponent(kind)}`,
    { content },
  );
}

export async function restorePrompt(
  name: string,
  kind: PromptKind = 'system',
): Promise<{ name: string; modified: boolean; restored: boolean; kind: PromptKind }> {
  return apiPost(
    `/config/prompts/${encodeURIComponent(name)}/restore?kind=${encodeURIComponent(kind)}`,
  );
}

export async function getSessionEvaluation(
  sessionId: string,
): Promise<SessionEvaluation> {
  return apiGet(`/research/${encodeURIComponent(sessionId)}/evaluation`);
}

import { ApiError } from '@/api/client';
import { toCamelCase, toSnakeCase } from '@/api/transform';
import type { CompanyProfile, ToolCard } from '../types';

const BASE = '/api/v2/enterprise';
const TOKEN_KEY = 'vigilador-enterprise-token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): HeadersInit {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: authHeaders(),
    body: body !== undefined ? JSON.stringify(toSnakeCase(body)) : undefined,
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => undefined);
    throw new ApiError(res.status, res.statusText, errorBody);
  }
  if (res.status === 204) return undefined as T;
  const raw = await res.json();
  return toCamelCase<T>(raw);
}

export async function login(username: string, password: string): Promise<{ token: string; username: string }> {
  const data = await request<{ token: string; username: string }>('POST', '/auth/login', { username, password });
  setToken(data.token);
  return data;
}

export async function logout(): Promise<void> {
  await request<void>('POST', '/auth/logout');
  clearToken();
}

export async function saveCompany(profile: CompanyProfile): Promise<void> {
  await request<void>('POST', '/onboarding/company', profile);
}

export async function saveLlmProvider(provider: string, apiKey: string, model?: string): Promise<{ status: string; provider: string }> {
  return request('POST', '/onboarding/llm-provider', { provider, apiKey, model });
}

export async function testLlm(provider?: string): Promise<{ status: string; model?: string; latencyMs?: number; error?: string }> {
  return request('POST', '/onboarding/test-llm', provider ? { provider } : {});
}

export async function getTools(detail: 'card' | 'summary' | 'docs' = 'card'): Promise<ToolCard[]> {
  return request('GET', `/tools?detail=${detail}`);
}

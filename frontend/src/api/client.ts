import { toCamelCase, toSnakeCase } from './transform';

export const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? '/api/v2' : 'http://localhost:8000/api/v2');

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

function baseHeaders(): HeadersInit {
  return { 'Content-Type': 'application/json' };
}

export class ApiError extends Error {
  readonly status: number;
  readonly body?: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  signal?.addEventListener('abort', () => controller.abort(), { once: true });

  try {
    // Request interceptor: convert camelCase body to snake_case for backend
    const snakeBody = body !== undefined ? toSnakeCase<unknown>(body) : undefined;

    const response = await fetch(buildUrl(path), {
      method,
      headers: baseHeaders(),
      body: snakeBody !== undefined ? JSON.stringify(snakeBody) : undefined,
      signal: controller.signal,
    });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => undefined);
      throw new ApiError(response.status, response.statusText, errorBody);
    }
    // Response interceptor: convert snake_case response to camelCase
    const raw = await response.json();
    return toCamelCase<T>(raw);
  } finally {
    clearTimeout(timeout);
  }
}

export async function apiGet<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>('GET', path, undefined, signal);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>('POST', path, body, signal);
}

export async function apiPatch<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>('PATCH', path, body, signal);
}

export async function apiPut<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>("PUT", path, body, signal);
}

export async function apiDel<T = unknown>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>('DELETE', path, undefined, signal);
}

export async function apiUpload<T = unknown>(
  path: string,
  file: File,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120_000);
  signal?.addEventListener('abort', () => controller.abort(), { once: true });

  try {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(buildUrl(path), {
      method: 'POST',
      body: form,
      signal: controller.signal,
    });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => undefined);
      throw new ApiError(response.status, response.statusText, errorBody);
    }
    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

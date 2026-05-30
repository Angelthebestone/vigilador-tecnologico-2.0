// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError } from '@/api/client';

// Provide a working localStorage mock
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value; },
  removeItem: (key: string) => { delete store[key]; },
  clear: () => { Object.keys(store).forEach(k => delete store[k]); },
  get length() { return Object.keys(store).length; },
  key: (i: number) => Object.keys(store)[i] ?? null,
};
vi.stubGlobal('localStorage', localStorageMock);

import {
  getToken,
  setToken,
  clearToken,
  login,
  logout,
  saveCompany,
  saveLlmProvider,
  testLlm,
  getTools,
} from '../api/enterpriseClient';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
  localStorageMock.clear();
});

function okJson(data: unknown, status = 200) {
  return { ok: true, status, json: () => Promise.resolve(data) };
}

function ok204() {
  return { ok: true, status: 204, json: () => Promise.resolve(undefined) };
}

describe('token helpers', () => {
  it('getToken returns null when empty', () => {
    expect(getToken()).toBeNull();
  });

  it('setToken stores and getToken retrieves', () => {
    setToken('abc');
    expect(getToken()).toBe('abc');
  });

  it('clearToken removes token', () => {
    setToken('abc');
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe('login', () => {
  it('posts credentials and stores token', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ token: 't1', username: 'u1' }));
    const res = await login('u1', 'p1');
    expect(res).toEqual({ token: 't1', username: 'u1' });
    expect(getToken()).toBe('t1');
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/enterprise/auth/login',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

describe('logout', () => {
  it('posts and clears token', async () => {
    setToken('t1');
    mockFetch.mockResolvedValueOnce(ok204());
    await logout();
    expect(getToken()).toBeNull();
  });
});

describe('Authorization header', () => {
  it('includes Bearer token when set', async () => {
    setToken('mytoken');
    mockFetch.mockResolvedValueOnce(ok204());
    await logout();
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers['Authorization']).toBe('Bearer mytoken');
  });

  it('omits Authorization when no token', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ token: 'x', username: 'u' }));
    await login('u', 'p');
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers['Authorization']).toBeUndefined();
  });
});

describe('saveCompany', () => {
  it('posts company profile', async () => {
    setToken('t');
    mockFetch.mockResolvedValueOnce(ok204());
    await saveCompany({ name: 'Acme' });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/enterprise/onboarding/company',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

describe('saveLlmProvider', () => {
  it('posts provider and returns result', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ status: 'ok', provider: 'openai' }));
    const res = await saveLlmProvider('openai', 'key1', 'gpt-4');
    expect(res).toEqual({ status: 'ok', provider: 'openai' });
  });
});

describe('testLlm', () => {
  it('returns success payload', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ status: 'ok', model: 'gpt-4', latency_ms: 120 }));
    const res = await testLlm('openai');
    expect(res.status).toBe('ok');
    expect(res.latencyMs).toBe(120);
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({ detail: 'fail' }),
    });
    await expect(testLlm()).rejects.toBeInstanceOf(ApiError);
  });
});

describe('getTools', () => {
  it('fetches tools with default detail=card', async () => {
    mockFetch.mockResolvedValueOnce(okJson([{ id: '1', description: 'd', domains: [], requires_auth: false, cost_tier: 'free', status: 'active' }]));
    const res = await getTools();
    expect(res[0].id).toBe('1');
    expect(res[0].requiresAuth).toBe(false);
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/enterprise/tools?detail=card',
      expect.objectContaining({ method: 'GET' }),
    );
  });
});

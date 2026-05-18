import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiGet, apiPost, apiPatch, apiDel, ApiError, API_BASE } from '../client';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('apiGet', () => {
  it('makes GET request to correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiGet('/sessions/abc');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/sessions/abc`,
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('includes Content-Type header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiGet('/sessions/abc');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    );
  });
});

describe('apiPost', () => {
  it('makes POST request to correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost('/sessions', {});

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/sessions`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('sends body with correct Content-Type header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost('/sessions', { query: 'test' });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: expect.any(String),
      }),
    );
  });
});

describe('apiPatch', () => {
  it('makes PATCH request to correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPatch('/sessions/abc', { status: 'approved' });

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/sessions/abc`,
      expect.objectContaining({ method: 'PATCH' }),
    );
  });
});

describe('apiDel', () => {
  it('makes DELETE request to correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiDel('/sessions/abc');

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/sessions/abc`,
      expect.objectContaining({ method: 'DELETE' }),
    );
  });
});

describe('response interceptor (snake_case → camelCase)', () => {
  it('converts flat snake_case keys to camelCase', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        session_id: 'abc',
        user_query: 'test',
        confidence_score: 0.95,
      }),
    });

    const result = await apiGet<Record<string, unknown>>('/test');

    expect(result).toEqual({
      sessionId: 'abc',
      userQuery: 'test',
      confidenceScore: 0.95,
    });
  });

  it('converts nested snake_case objects recursively', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        session_id: 'abc',
        plan: {
          requires_approval: true,
          global_constraints: { max_sources: 15 },
        },
      }),
    });

    const result = await apiGet<{ sessionId: string; plan: { requiresApproval: boolean; globalConstraints: { maxSources: number } } }>('/test');

    expect(result.sessionId).toBe('abc');
    expect(result.plan.requiresApproval).toBe(true);
    expect(result.plan.globalConstraints.maxSources).toBe(15);
  });

  it('converts arrays of snake_case objects', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        sources: [
          { source_id: 1, source_name: 'Alpha' },
          { source_id: 2, source_name: 'Beta' },
        ],
      }),
    });

    const result = await apiGet<{ sources: Array<{ sourceId: number; sourceName: string }> }>('/sources');

    expect(result.sources).toHaveLength(2);
    expect(result.sources[0].sourceId).toBe(1);
    expect(result.sources[0].sourceName).toBe('Alpha');
    expect(result.sources[1].sourceName).toBe('Beta');
  });
});

describe('request interceptor (camelCase → snake_case)', () => {
  it('converts flat camelCase body to snake_case before sending', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost('/test', { approved: true, currentStatus: 'active' });

    const [, options] = mockFetch.mock.calls[0];
    const sentBody = JSON.parse(options.body as string);

    expect(sentBody).toEqual({
      approved: true,
      current_status: 'active',
    });
  });

  it('converts nested camelCase body recursively', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost('/test', {
      sessionId: 'abc',
      scope: { timeHorizon: 'short', region: 'global' },
    });

    const [, options] = mockFetch.mock.calls[0];
    const sentBody = JSON.parse(options.body as string);

    expect(sentBody).toEqual({
      session_id: 'abc',
      scope: { time_horizon: 'short', region: 'global' },
    });
  });
});

describe('null/undefined handling', () => {
  it('handles null response body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(null),
    });

    const result = await apiGet<unknown>('/test');
    expect(result).toBeNull();
  });

  it('sends undefined body when body is undefined', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost<Record<string, unknown>>('/test', undefined);

    const [, options] = mockFetch.mock.calls[0];
    expect(options.body).toBeUndefined();
  });

  it('stringifies null body as "null"', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiPost<Record<string, unknown>>('/test', null);

    const [, options] = mockFetch.mock.calls[0];
    expect(options.body).toBe('null');
  });
});

describe('array response handling', () => {
  it('converts array of snake_case objects from response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([
        { source_id: 1, relevance_score: 0.9 },
        { source_id: 2, relevance_score: 0.7 },
      ]),
    });

    const result = await apiGet<Array<{ sourceId: number; relevanceScore: number }>>('/sources/list');

    expect(result).toHaveLength(2);
    expect(result[0].sourceId).toBe(1);
    expect(result[0].relevanceScore).toBe(0.9);
    expect(result[1].relevanceScore).toBe(0.7);
  });
});

describe('error handling', () => {
  it('throws ApiError on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid session ID' }),
    });

    const err = await apiGet<unknown>('/test').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 400,
      body: { detail: 'Invalid session ID' },
    });
  });

  it('throws ApiError with undefined body when json parse fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('parse error')),
    });

    await expect(apiGet('/test')).rejects.toMatchObject({
      status: 500,
      body: undefined,
    });
  });

  it('throws ApiError on 404', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail: 'Not found' }),
    });

    await expect(apiGet('/missing')).rejects.toMatchObject({
      status: 404,
    });
  });
});

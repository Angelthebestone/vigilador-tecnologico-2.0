import { describe, it, expect } from 'vitest';
import { snakeToCamel, camelToSnake, toCamelCase, toSnakeCase } from '../transform';

describe('snakeToCamel', () => {
  it('converts simple snake_case to camelCase', () => {
    expect(snakeToCamel('session_id')).toBe('sessionId');
    expect(snakeToCamel('user_query')).toBe('userQuery');
    expect(snakeToCamel('confidence_score')).toBe('confidenceScore');
  });

  it('keeps already camelCase strings unchanged', () => {
    expect(snakeToCamel('sessionId')).toBe('sessionId');
    expect(snakeToCamel('id')).toBe('id');
  });

  it('preserves all-caps acronyms', () => {
    expect(snakeToCamel('URL')).toBe('URL');
    expect(snakeToCamel('API_BASE')).toBe('API_BASE');
  });

  it('handles single word', () => {
    expect(snakeToCamel('id')).toBe('id');
    expect(snakeToCamel('status')).toBe('status');
  });

  it('handles empty string', () => {
    expect(snakeToCamel('')).toBe('');
  });
});

describe('camelToSnake', () => {
  it('converts simple camelCase to snake_case', () => {
    expect(camelToSnake('sessionId')).toBe('session_id');
    expect(camelToSnake('userQuery')).toBe('user_query');
    expect(camelToSnake('confidenceScore')).toBe('confidence_score');
  });

  it('keeps already snake_case strings unchanged', () => {
    expect(camelToSnake('session_id')).toBe('session_id');
    expect(camelToSnake('id')).toBe('id');
  });

  it('lowercases all-caps strings', () => {
    expect(camelToSnake('URL')).toBe('url');
  });

  it('handles single word', () => {
    expect(camelToSnake('id')).toBe('id');
    expect(camelToSnake('status')).toBe('status');
  });

  it('handles empty string', () => {
    expect(camelToSnake('')).toBe('');
  });
});

describe('toCamelCase (recursive)', () => {
  it('converts flat object keys', () => {
    const input = { session_id: 'abc', user_query: 'test', confidence_score: 0.95 };
    const expected = { sessionId: 'abc', userQuery: 'test', confidenceScore: 0.95 };
    expect(toCamelCase(input)).toEqual(expected);
  });

  it('converts nested objects recursively', () => {
    const input = {
      session_id: 'abc',
      user_query: 'test',
      plan: {
        plan_id: 'p1',
        requires_approval: true,
        global_constraints: { max_sources: 15 },
      },
    };
    const result = toCamelCase(input);
    expect(result).toHaveProperty('sessionId', 'abc');
    expect(result).toHaveProperty('plan.planId', 'p1');
    expect(result).toHaveProperty('plan.requiresApproval', true);
    expect((result as any).plan.globalConstraints).toHaveProperty('maxSources', 15);
  });

  it('converts arrays of objects', () => {
    const input = {
      providers: [
        { provider_name: 'tavily', avg_latency_ms: 843, error_rate: 0.02 },
        { provider_name: 'arxiv', avg_latency_ms: 612, error_rate: 0.01 },
      ],
    };
    const result = toCamelCase<{ providers: Array<{ providerName: string }> }>(input);
    expect(result.providers).toHaveLength(2);
    expect(result.providers[0].providerName).toBe('tavily');
    expect(result.providers[1].errorRate).toBe(0.01);
  });

  it('preserves null and undefined', () => {
    expect(toCamelCase(null)).toBeNull();
    expect(toCamelCase(undefined)).toBeUndefined();
  });

  it('preserves primitives', () => {
    expect(toCamelCase(42)).toBe(42);
    expect(toCamelCase('hello')).toBe('hello');
    expect(toCamelCase(true)).toBe(true);
  });

  it('handles empty objects and arrays', () => {
    expect(toCamelCase({})).toEqual({});
    expect(toCamelCase([])).toEqual([]);
  });

  it('preserves Date objects', () => {
    const date = new Date('2024-01-01');
    expect(toCamelCase(date)).toBe(date);
  });

  it('converts real-world snake_case API response', () => {
    const backendResponse = {
      session_id: 'abc-123',
      status: 'EXECUTING',
      plan: {
        id: 'plan-1',
        version: 1,
        requires_approval: true,
        global_constraints: {
          max_sources_per_branch: 15,
          min_confidence_threshold: 0.65,
          output_language: 'es',
        },
        branches: [
          {
            branch_type: 'AVANCES',
            focus_queries: ['query1', 'query2'],
            mcp_providers: ['tavily', 'exa'],
            priority_weight: 1.2,
          },
        ],
      },
    };
    const result = toCamelCase(backendResponse);
    expect(result).toHaveProperty('sessionId', 'abc-123');
    expect(result).toHaveProperty('plan.requiresApproval', true);
    expect((result as any).plan.globalConstraints.maxSourcesPerBranch).toBe(15);
    expect((result as any).plan.branches[0].branchType).toBe('AVANCES');
    expect((result as any).plan.branches[0].mcpProviders).toEqual(['tavily', 'exa']);
  });
});

describe('toSnakeCase (recursive)', () => {
  it('converts flat object keys', () => {
    const input = { sessionId: 'abc', userQuery: 'test', confidenceScore: 0.95 };
    const expected = { session_id: 'abc', user_query: 'test', confidence_score: 0.95 };
    expect(toSnakeCase(input)).toEqual(expected);
  });

  it('converts nested objects recursively', () => {
    const input = {
      sessionId: 'abc',
      plan: {
        planId: 'p1',
        requiresApproval: true,
        globalConstraints: { maxSources: 15 },
      },
    };
    const result = toSnakeCase(input);
    expect(result).toHaveProperty('session_id', 'abc');
    expect(result).toHaveProperty('plan.plan_id', 'p1');
    expect((result as any).plan.global_constraints.max_sources).toBe(15);
  });

  it('converts arrays of objects', () => {
    const input = {
      providers: [
        { providerName: 'tavily', avgLatencyMs: 843 },
        { providerName: 'arxiv', avgLatencyMs: 612 },
      ],
    };
    const result = toSnakeCase(input);
    expect((result as any).providers[0].provider_name).toBe('tavily');
    expect((result as any).providers[1].avg_latency_ms).toBe(612);
  });

  it('preserves null and undefined', () => {
    expect(toSnakeCase(null)).toBeNull();
    expect(toSnakeCase(undefined)).toBeUndefined();
  });

  it('handles empty objects and arrays', () => {
    expect(toSnakeCase({})).toEqual({});
    expect(toSnakeCase([])).toEqual([]);
  });

  it('converts real-world frontend camelCase body', () => {
    const frontendBody = {
      approved: true,
      scope: {
        region: 'global',
        timeHorizon: 'short',
      },
    };
    const result = toSnakeCase(frontendBody);
    expect(result).toHaveProperty('approved', true);
    expect((result as any).scope.region).toBe('global');
    expect((result as any).scope.time_horizon).toBe('short');
  });
});

describe('roundtrip: snake → camel → snake', () => {
  it('preserves data through full roundtrip', () => {
    const original = {
      session_id: 'abc',
      user_query: 'test',
      nested: {
        confidence_score: 0.95,
        requires_approval: true,
      },
      items: [
        { item_id: 1, item_name: 'test' },
      ],
    };
    const camel = toCamelCase(original);
    const back = toSnakeCase(camel);
    expect(back).toEqual(original);
  });
});

/**
 * Transform layer: snake_case ↔ camelCase conversion for API communication.
 *
 * The backend (Python/FastAPI) returns keys in snake_case, while the
 * frontend (TypeScript/React) expects camelCase. This module provides
 * recursive conversion functions that handle nested objects, arrays,
 * null/undefined, and edge cases.
 *
 * Usage:
 *   const camelData = toCamelCase(snakeData);    // response interceptor
 *   const snakeBody = toSnakeCase(camelBody);     // request interceptor
 */

// ---------------------------------------------------------------------------
// Regex: matches full snake_case segments (one or more lowercase words
// separated by underscore), plus a leading digit-safe marker.
// ---------------------------------------------------------------------------
const SNAKE_RE = /_([a-z])/g;
const CAMEL_RE = /[A-Z]/g;

/**
 * Convert a single snake_case string to camelCase.
 * Examples:
 *   "session_id"    → "sessionId"
 *   "branch_kpis"   → "branchKpis"
 *   "confidence_score" → "confidenceScore"
 *   "id"            → "id" (no underscore)
 *   "URL"           → "URL" (all-caps preserved)
 */
export function snakeToCamel(key: string): string {
  // Preserve all-caps acronyms
  if (key === key.toUpperCase() && key.length > 1) return key;
  return key.replace(SNAKE_RE, (_, letter) => letter.toUpperCase());
}

/**
 * Convert a single camelCase string to snake_case.
 * Examples:
 *   "sessionId"        → "session_id"
 *   "branchKpis"       → "branch_kpis"
 *   "confidenceScore"  → "confidence_score"
 *   "id"               → "id"
 *   "URL"              → "url" (lowercased)
 */
export function camelToSnake(key: string): string {
  if (key === key.toLowerCase()) return key;
  return key
    .replace(CAMEL_RE, (letter) => `_${letter.toLowerCase()}`)
    .replace(/^_/, '');
}

/**
 * Recursively convert all keys in an object from snake_case to camelCase.
 * Handles:
 *   - Plain objects (nested any depth)
 *   - Arrays (each element converted)
 *   - null / undefined (returned as-is)
 *   - Primitives (string, number, boolean — returned as-is)
 *   - Date objects (preserved)
 */
export function toCamelCase<T>(value: unknown): T {
  if (value === null || value === undefined) return value as T;
  if (value instanceof Date) return value as unknown as T;
  if (Array.isArray(value)) {
    return value.map((item) => toCamelCase<unknown>(item)) as unknown as T;
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    const result: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      result[snakeToCamel(key)] = toCamelCase<unknown>(val);
    }
    return result as T;
  }
  return value as T;
}

/**
 * Recursively convert all keys in an object from camelCase to snake_case.
 * Same rules as toCamelCase but in reverse.
 */
export function toSnakeCase<T>(value: unknown): T {
  if (value === null || value === undefined) return value as T;
  if (value instanceof Date) return value as unknown as T;
  if (Array.isArray(value)) {
    return value.map((item) => toSnakeCase<unknown>(item)) as unknown as T;
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    const result: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      result[camelToSnake(key)] = toSnakeCase<unknown>(val);
    }
    return result as T;
  }
  return value as T;
}

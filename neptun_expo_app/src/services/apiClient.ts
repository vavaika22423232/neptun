import { absoluteUrl } from '../config/api';
import { appLogger } from '../core/logging/appLogger';
import {
  noteV1MonetizationHttpError,
} from '../features/monetization/services/monetizationBackend';
import { safeJson } from '../utils/json';
import { ApiError, fetchJson, mergeAbortSignals } from './apiHttp';

export { ApiError } from './apiHttp';

const API_LOG_COOLDOWN_MS = 60_000;
const lastApiLogAt = new Map<string, number>();

function isV1MonetizationPath(path: string): boolean {
  return path.startsWith('/api/v1/');
}

function shouldLogApiFailure(path: string, status?: number): boolean {
  const key = `${path}:${status ?? 'network'}`;
  const now = Date.now();
  const prev = lastApiLogAt.get(key) ?? 0;
  if (now - prev < API_LOG_COOLDOWN_MS) return false;
  lastApiLogAt.set(key, now);
  return true;
}

/** Do not hammer the backend when it is temporarily unavailable. */
export function isServerUnavailableStatus(status?: number): boolean {
  return status != null && status >= 500;
}

export type ApiRequestOptions = RequestInit & {
  timeoutMs?: number;
  authToken?: string | null;
  moderatorSecret?: string | null;
};

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { authToken, moderatorSecret, headers, ...init } = options;
  try {
    return await fetchJson<T>(absoluteUrl(path), {
      ...init,
      headers: {
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : null),
        ...(moderatorSecret ? { 'X-Auth-Secret': moderatorSecret } : null),
        ...headers,
      },
    });
  } catch (e) {
    if (e instanceof ApiError) {
      const shouldLog = shouldLogApiFailure(path, e.status);
      if (isV1MonetizationPath(path)) noteV1MonetizationHttpError(e);
      if (shouldLog) {
        appLogger.error('api', `${init.method ?? 'GET'} ${path}: ${e.message}`);
      }
    }
    throw e;
  }
}

export async function apiGet<T>(path: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T> {
  try {
    return await apiRequest<T>(path, { ...options, method: 'GET' });
  } catch (first) {
    if (first instanceof ApiError && first.status != null) throw first;
    return apiRequest<T>(path, { ...options, method: 'GET' });
  }
}

export async function apiGetWithEtag<T>(
  path: string,
  etag: string | null,
  timeoutMs = 8000,
  externalSignal?: AbortSignal | null,
): Promise<{ status: 200 | 304; etag: string | null; data?: T }> {
  const { signal, cleanup } = mergeAbortSignals(timeoutMs, externalSignal);
  try {
    const response = await fetch(absoluteUrl(path), {
      signal,
      headers: {
        Accept: 'application/json',
        ...(etag ? { 'If-None-Match': etag } : null),
      },
    });
    if (response.status === 304) return { status: 304, etag };
    if (!response.ok) throw new ApiError(`HTTP ${response.status}`, { status: response.status });
    const text = await response.text();
    return {
      status: 200,
      etag: response.headers.get('etag'),
      data: text.length ? safeJson<T>(text, {} as T) : undefined,
    };
  } catch (e) {
    if (signal.aborted) {
      throw new ApiError(externalSignal?.aborted ? 'Request aborted' : 'Request timed out', { cause: e });
    }
    throw e instanceof ApiError ? e : new ApiError(e instanceof Error ? e.message : 'Network error', { cause: e });
  } finally {
    cleanup();
  }
}

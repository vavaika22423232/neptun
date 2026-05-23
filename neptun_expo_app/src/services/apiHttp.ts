import { safeJson } from '../utils/json';

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, opts?: { status?: number; cause?: unknown }) {
    super(message);
    this.name = 'ApiError';
    this.status = opts?.status;
    if (opts?.cause) this.cause = opts.cause;
  }
}

export type HttpRequestOptions = RequestInit & {
  timeoutMs?: number;
};

export function mergeAbortSignals(timeoutMs: number, external?: AbortSignal | null): {
  signal: AbortSignal;
  cleanup: () => void;
} {
  const timeoutAc = new AbortController();
  const id = setTimeout(() => timeoutAc.abort(), timeoutMs);
  const onExternalAbort = () => timeoutAc.abort();
  external?.addEventListener('abort', onExternalAbort);
  return {
    signal: timeoutAc.signal,
    cleanup: () => {
      clearTimeout(id);
      external?.removeEventListener('abort', onExternalAbort);
    },
  };
}

export async function fetchJson<T>(url: string, options: HttpRequestOptions = {}): Promise<T> {
  const { timeoutMs = 15000, signal: externalSignal, headers, ...init } = options;
  const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
  const { signal, cleanup } = mergeAbortSignals(timeoutMs, externalSignal);

  try {
    const response = await fetch(url, {
      ...init,
      signal,
      headers: {
        Accept: 'application/json',
        ...(init.body && !isFormData ? { 'Content-Type': 'application/json' } : null),
        ...headers,
      },
    });
    const text = await response.text();
    const data = text.length ? safeJson<unknown>(text, null) : null;
    if (!response.ok) {
      const message =
        data && typeof data === 'object' && data !== null && 'error' in data
          ? String((data as { error: unknown }).error)
          : `HTTP ${response.status}`;
      throw new ApiError(message, { status: response.status });
    }
    return data as T;
  } catch (e) {
    if (signal.aborted) {
      const aborted = externalSignal?.aborted;
      throw new ApiError(aborted ? 'Request aborted' : 'Request timed out', { cause: e });
    }
    if (e instanceof ApiError) throw e;
    throw new ApiError(e instanceof Error ? e.message : 'Network error', { cause: e });
  } finally {
    cleanup();
  }
}

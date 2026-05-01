/**
 * Shared marker store state on `globalThis` (PM2 / Next standalone module isolation).
 * @see markers-store.ts
 */

export interface MarkerStoreState {
  messages: Record<string, unknown>[];
  initialized: boolean;
  initPromise: Promise<void> | null;
  lastIngestTime: number;
  pollTimer: ReturnType<typeof setInterval> | null;
  lastVersion: number;
  writeLock: Promise<void>;
}

export const MARKER_STORE_GLOBAL_KEY = '__neptun_marker_store__';

export function getMarkerStoreState(): MarkerStoreState {
  const g = globalThis as Record<string, unknown>;
  if (!g[MARKER_STORE_GLOBAL_KEY]) {
    g[MARKER_STORE_GLOBAL_KEY] = {
      messages: [],
      initialized: false,
      initPromise: null,
      lastIngestTime: 0,
      pollTimer: null,
      lastVersion: 0,
      writeLock: Promise.resolve(),
    } as MarkerStoreState;
  }
  return g[MARKER_STORE_GLOBAL_KEY] as MarkerStoreState;
}

/** Serialize disk writes across concurrent ingest paths. */
export function withMarkerWriteLock<T>(fn: () => Promise<T>): Promise<T> {
  const state = getMarkerStoreState();
  const prev = state.writeLock;
  let resolve!: () => void;
  state.writeLock = new Promise<void>((r) => {
    resolve = r;
  });
  return prev.then(fn).finally(() => resolve());
}

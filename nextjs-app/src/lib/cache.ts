import crypto from 'crypto';
import { publishMarkerDerivedCacheInvalidate } from '@/lib/redis';

// ============================================
// In-memory TTL cache for API routes
// ============================================

interface CacheEntry<T> {
  data: T;
  json: string;   // pre-serialized JSON (avoids double-stringify)
  etag: string;
  timestamp: number;
  ttl: number;
}

class MemoryCache {
  private store: Map<string, CacheEntry<unknown>> = new Map();

  get<T>(key: string): CacheEntry<T> | null {
    const entry = this.store.get(key) as CacheEntry<T> | undefined;
    if (!entry) return null;

    if (Date.now() - entry.timestamp > entry.ttl) {
      this.store.delete(key);
      return null;
    }

    return entry;
  }

  set<T>(key: string, data: T, ttlMs: number): CacheEntry<T> {
    // Serialize once — reused for ETag hash and response body
    const json = JSON.stringify(data);
    const etag = `"${crypto.createHash('md5').update(json).digest('hex').slice(0, 16)}"`;

    const entry: CacheEntry<T> = {
      data,
      json,
      etag,
      timestamp: Date.now(),
      ttl: ttlMs,
    };

    this.store.set(key, entry as CacheEntry<unknown>);
    return entry;
  }

  /**
   * Get data if still fresh, otherwise return stale data if within stale TTL.
   */
  getWithStale<T>(key: string, staleTtlMs: number): { entry: CacheEntry<T> | null; isStale: boolean } {
    const entry = this.store.get(key) as CacheEntry<T> | undefined;
    if (!entry) return { entry: null, isStale: false };

    const age = Date.now() - entry.timestamp;
    if (age <= entry.ttl) {
      return { entry, isStale: false };
    }
    if (age <= staleTtlMs) {
      return { entry, isStale: true };
    }

    this.store.delete(key);
    return { entry: null, isStale: false };
  }

  delete(key: string) {
    this.store.delete(key);
  }

  clear() {
    this.store.clear();
  }
}

// Singleton cache instance
export const cache = new MemoryCache();

/** API response caches built from markers-store (must stay in sync across PM2 workers). */
export const MARKER_DERIVED_CACHE_KEYS = [
  'data_markers',
  'data_markers_extended',
  'threats_data',
  'threats_data_extended',
  'messages_mobile',
  'fusion_trajectories',
] as const;

/** Drop marker-derived HTTP cache entries on this Node process only (no Redis publish). */
export function clearMarkerDerivedApiCachesLocal(): void {
  for (const key of MARKER_DERIVED_CACHE_KEYS) {
    cache.delete(key);
  }
}

/**
 * Bust marker-derived API caches locally and on all PM2 workers (Redis pub/sub).
 * Use after writes to markers / admin settings that affect API shape.
 * On poll-only sync, prefer `clearMarkerDerivedApiCachesLocal()` to avoid redundant publishes.
 */
export function invalidateMarkerDerivedCaches(): void {
  clearMarkerDerivedApiCachesLocal();
  publishMarkerDerivedCacheInvalidate().catch(() => {
    /* Redis optional */
  });
}

/**
 * Generate ETag from data
 */
export function generateETag(data: unknown): string {
  const json = JSON.stringify(data);
  return `"${crypto.createHash('md5').update(json).digest('hex').slice(0, 16)}"`;
}

/**
 * Helper to create a Response with ETag support.
 * Returns 304 if client has matching ETag.
 * Uses pre-serialized JSON from cache entry when available.
 */
export function withETag(
  data: unknown,
  etag: string,
  clientETag: string | null,
  headers?: Record<string, string>,
  preSerializedJson?: string,
): Response {
  if (clientETag && clientETag === etag) {
    return new Response(null, { status: 304 });
  }

  const responseHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ETag: etag,
    'Cache-Control': 'no-cache, must-revalidate',
    ...headers,
  };

  // Use pre-serialized JSON if available (avoids second JSON.stringify)
  const body = preSerializedJson ?? JSON.stringify(data);

  return new Response(body, {
    status: 200,
    headers: responseHeaders,
  });
}

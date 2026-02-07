import crypto from 'crypto';

// ============================================
// In-memory TTL cache for API routes
// ============================================

interface CacheEntry<T> {
  data: T;
  etag: string;
  timestamp: number;
  ttl: number;
}

class MemoryCache {
  private store: Map<string, CacheEntry<unknown>> = new Map();

  get<T>(key: string): CacheEntry<T> | null {
    const entry = this.store.get(key) as CacheEntry<T> | undefined;
    if (!entry) return null;

    // Check if expired
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.store.delete(key);
      return null;
    }

    return entry;
  }

  set<T>(key: string, data: T, ttlMs: number): CacheEntry<T> {
    const json = JSON.stringify(data);
    const etag = `"${crypto.createHash('md5').update(json).digest('hex').slice(0, 16)}"`;

    const entry: CacheEntry<T> = {
      data,
      etag,
      timestamp: Date.now(),
      ttl: ttlMs,
    };

    this.store.set(key, entry as CacheEntry<unknown>);
    return entry;
  }

  /**
   * Get data if still fresh, otherwise return stale data if within stale TTL.
   * Useful for serving stale data while refreshing.
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

/**
 * Generate ETag from data
 */
export function generateETag(data: unknown): string {
  const json = JSON.stringify(data);
  return `"${crypto.createHash('md5').update(json).digest('hex').slice(0, 16)}"`;
}

/**
 * Helper to create a NextResponse with ETag support.
 * Returns 304 if client has matching ETag.
 */
export function withETag(
  data: unknown,
  etag: string,
  clientETag: string | null,
  headers?: Record<string, string>
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

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: responseHeaders,
  });
}

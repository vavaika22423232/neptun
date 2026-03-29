/**
 * Redis client singleton for persistent shared cache.
 *
 * Replaces the in-memory MemoryCache that was NOT shared between
 * Next.js instrumentation context and API route handlers in standalone mode.
 *
 * Redis solves three critical problems:
 * 1. Data survives process restarts (persistence)
 * 2. Shared between all Node.js contexts (instrumentation + routes)
 * 3. Fast reads (~0.1ms localhost) with no file I/O
 */

import Redis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';

// Lazy singleton — created on first use
let _redis: Redis | null = null;

export function getRedis(): Redis {
  if (!_redis) {
    _redis = new Redis(REDIS_URL, {
      maxRetriesPerRequest: null,
      retryStrategy(times) {
        // Exponential backoff: 100ms, 200ms, 400ms... up to 5s
        return Math.min(times * 100, 5000);
      },
      lazyConnect: false,
      enableReadyCheck: true,
      // Queue commands when Redis is down instead of failing immediately
      enableOfflineQueue: true,
    });

    _redis.on('error', (err) => {
      console.warn('[REDIS] Connection error:', err.message);
    });

    _redis.on('connect', () => {
      console.log('[REDIS] Connected');
    });
  }

  return _redis;
}

// ── High-level cache helpers ──────────────────────────────────────────────────

/**
 * Get JSON data from Redis. Returns null if key doesn't exist or expired.
 */
export async function redisGet<T>(key: string): Promise<T | null> {
  try {
    const raw = await getRedis().get(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch (err) {
    console.warn(`[REDIS] GET ${key} error:`, err);
    return null;
  }
}

/**
 * Set JSON data in Redis with TTL (seconds).
 */
export async function redisSet<T>(key: string, data: T, ttlSeconds: number): Promise<void> {
  try {
    const json = JSON.stringify(data);
    await getRedis().set(key, json, 'EX', ttlSeconds);
  } catch (err) {
    console.warn(`[REDIS] SET ${key} error:`, err);
  }
}

/**
 * Get JSON data with its remaining TTL.
 * Returns { data, ttl, age } where age = maxTTL - ttl.
 */
export async function redisGetWithMeta<T>(key: string, maxTtl: number): Promise<{
  data: T | null;
  ttl: number;      // seconds remaining
  age: number;       // seconds since last write
  raw: string | null;
}> {
  try {
    const redis = getRedis();
    const [raw, ttl] = await Promise.all([
      redis.get(key),
      redis.ttl(key),
    ]);

    if (!raw || ttl < 0) {
      return { data: null, ttl: 0, age: maxTtl, raw: null };
    }

    return {
      data: JSON.parse(raw) as T,
      ttl,
      age: maxTtl - ttl,
      raw,
    };
  } catch (err) {
    console.warn(`[REDIS] GET+META ${key} error:`, err);
    return { data: null, ttl: 0, age: maxTtl, raw: null };
  }
}

/**
 * Increment a numeric key. Returns the new value after increment.
 * Creates key at 0 if missing, then increments to 1.
 */
export async function redisIncr(key: string): Promise<number> {
  try {
    return await getRedis().incr(key);
  } catch (err) {
    console.warn(`[REDIS] INCR ${key} error:`, err);
    return 0;
  }
}

/**
 * Decrement a numeric key. Returns the new value after decrement.
 * Clamps to 0 if key would go negative (e.g. worker crash without DECR).
 */
export async function redisDecr(key: string): Promise<number> {
  try {
    const val = await getRedis().decr(key);
    if (val < 0) {
      await getRedis().set(key, '0');
      return 0;
    }
    return val;
  } catch (err) {
    console.warn(`[REDIS] DECR ${key} error:`, err);
    return 0;
  }
}

/**
 * Get numeric value of a key. Returns 0 if missing or invalid.
 */
export async function redisGetCount(key: string): Promise<number> {
  try {
    const val = await getRedis().get(key);
    if (val == null) return 0;
    const n = parseInt(val, 10);
    return Number.isNaN(n) ? 0 : Math.max(0, n);
  } catch (err) {
    console.warn(`[REDIS] GET ${key} error:`, err);
    return 0;
  }
}

/**
 * Check if Redis is healthy.
 */
export async function redisHealthy(): Promise<boolean> {
  try {
    const pong = await getRedis().ping();
    return pong === 'PONG';
  } catch {
    return false;
  }
}

// ── Pub/Sub for cross-process SSE broadcast ──────────────────────────────────

// Separate Redis connection for subscriptions (required by Redis protocol)
let _redisSub: Redis | null = null;

function getSubscriber(): Redis {
  if (!_redisSub) {
    _redisSub = new Redis(REDIS_URL, {
      maxRetriesPerRequest: null, // subscriber must never time out
      retryStrategy(times) {
        return Math.min(times * 100, 5000);
      },
      lazyConnect: false,
      enableReadyCheck: true,
      enableOfflineQueue: true,
    });

    _redisSub.on('error', (err) => {
      console.warn('[REDIS-SUB] Connection error:', err.message);
    });
  }

  return _redisSub;
}

const SSE_CHANNEL = 'sse:broadcast';
const CHAT_CACHE_INV_CHANNEL = 'neptun:chat_cache_inv';
const MARKER_DERIVED_INV_CHANNEL = 'neptun:marker_api_cache_inv';

const sseSubscribers = new Set<(event: { type: string; data: unknown }) => void>();
const chatCacheInvSubscribers = new Set<() => void>();
const markerDerivedInvSubscribers = new Set<() => void>();
let subscriberMessageWired = false;
let subscriberChannelsJoined = false;

function wireSubscriberMessageRouter(): void {
  if (subscriberMessageWired) return;
  subscriberMessageWired = true;
  const sub = getSubscriber();
  sub.on('message', (channel, message) => {
    if (channel === CHAT_CACHE_INV_CHANNEL) {
      for (const fn of chatCacheInvSubscribers) {
        try {
          fn();
        } catch {
          /* ignore */
        }
      }
      return;
    }
    if (channel !== SSE_CHANNEL) return;
    try {
      const event = JSON.parse(message) as { type: string; data: unknown };
      for (const cb of sseSubscribers) {
        try {
          cb(event);
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore malformed */
    }
  });
}

function ensurePubSubChannelsSubscribed(): void {
  if (subscriberChannelsJoined) return;
  subscriberChannelsJoined = true;
  const sub = getSubscriber();
  sub.subscribe(SSE_CHANNEL, CHAT_CACHE_INV_CHANNEL, MARKER_DERIVED_INV_CHANNEL, (err) => {
    if (err) {
      console.error('[REDIS-SUB] Subscribe error:', err);
    } else {
      console.log('[REDIS-SUB] Subscribed to SSE + cache invalidation channels');
    }
  });
}

/**
 * Publish an SSE event to all Node.js workers via Redis Pub/Sub.
 */
export async function publishSSE(event: { type: string; data: unknown }): Promise<void> {
  try {
    await getRedis().publish(SSE_CHANNEL, JSON.stringify(event));
  } catch (err) {
    console.warn('[REDIS] Publish error:', err);
  }
}

/** Notify all Node workers to drop in-memory chat message cache (PM2 cluster). */
export async function publishChatCacheInvalidate(): Promise<void> {
  try {
    await getRedis().publish(CHAT_CACHE_INV_CHANNEL, '1');
  } catch (err) {
    console.warn('[REDIS] Chat cache invalidate publish error:', err);
  }
}

/** Notify all Node workers to drop /api/data-style memory caches (PM2 cluster). */
export async function publishMarkerDerivedCacheInvalidate(): Promise<void> {
  try {
    await getRedis().publish(MARKER_DERIVED_INV_CHANNEL, '1');
  } catch (err) {
    console.warn('[REDIS] Marker-derived cache invalidate publish error:', err);
  }
}

/**
 * Subscribe to SSE events from other workers.
 * The callback receives already-parsed event objects.
 * Safe to call multiple times — handlers are accumulated (chat/stream uses one).
 */
export function subscribeSSE(
  callback: (event: { type: string; data: unknown }) => void
): void {
  wireSubscriberMessageRouter();
  sseSubscribers.add(callback);
  ensurePubSubChannelsSubscribed();
}

/**
 * Clear local chat JSON cache on all workers when any worker writes messages.
 * Call once per process from instrumentation.
 */
export function subscribeChatCacheInvalidation(onInvalidate: () => void): void {
  wireSubscriberMessageRouter();
  chatCacheInvSubscribers.add(onInvalidate);
  ensurePubSubChannelsSubscribed();
}

/** Clear local marker-derived API caches when another worker ingests (see cache.ts). */
export function subscribeMarkerDerivedCacheInvalidation(onInvalidate: () => void): void {
  wireSubscriberMessageRouter();
  markerDerivedInvSubscribers.add(onInvalidate);
  ensurePubSubChannelsSubscribed();
}

/**
 * Background alarm fetcher for Node.js server side.
 *
 * Fetches alarms every 10s from ukrainealarm.com API, stores in Redis,
 * and broadcasts changes to all SSE clients. Redis ensures data survives
 * restarts and is shared between all Node.js contexts.
 */

import { redisSet, redisGet, getRedis } from './redis';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import crypto from 'crypto';

const ALARM_API_BASE = 'https://api.ukrainealarm.com/api/v3';
const ALARM_API_KEY = process.env.ALARM_API_KEY || process.env.ALARMS_API_KEY || '';
const FETCH_INTERVAL = 20_000; // 20s — Ukraine Alarm API (less CPU / fewer external calls)
const REDIS_KEY = 'alarms:all';
const REDIS_TTL = 1800; // 30 minutes — extended fallback during API 401 streaks
const REDIS_META_KEY = 'alarms:last_updated';
const RETRY_ATTEMPTS = 3; // retries per 10s tick
const RETRY_DELAYS = [1000, 2000, 3000]; // backoff between retries
/** Only one Node process hits Ukraine Alarm API per tick (PM2 cluster / multiple workers). */
const FETCH_LOCK_KEY = 'alarms:bg_fetch_lock';
const FETCH_LOCK_TTL_SEC = 35;

let intervalId: ReturnType<typeof setInterval> | null = null;
let lastETag: string | null = null;

/**
 * Single attempt to fetch alarms from the API.
 */
async function singleFetch(): Promise<unknown[] | null> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8_000);

  try {
    const response = await fetch(`${ALARM_API_BASE}/alerts`, {
      headers: { Authorization: ALARM_API_KEY },
      signal: controller.signal,
      cache: 'no-store',
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn(`[ALARM-BG] API returned ${response.status}`);
      return null;
    }

    const data = await response.json();
    return Array.isArray(data) ? data : null;
  } catch (err) {
    clearTimeout(timeoutId);
    console.warn('[ALARM-BG] Fetch error:', err);
    return null;
  }
}

/**
 * Extend TTL on existing Redis cache to prevent data loss during API outages.
 */
async function acquireFetchLeaderLock(): Promise<boolean> {
  if (process.env.DISABLE_ALARM_FETCH_LOCK === '1') return true;
  try {
    const ok = await getRedis().set(FETCH_LOCK_KEY, String(process.pid), 'EX', FETCH_LOCK_TTL_SEC, 'NX');
    return ok === 'OK';
  } catch (err) {
    console.warn('[ALARM-BG] Leader lock Redis error — fetching without lock:', err);
    return true;
  }
}

async function extendCacheTTL(): Promise<void> {
  try {
    const redis = getRedis();
    const exists = await redis.exists(REDIS_KEY);
    if (exists) {
      await redis.expire(REDIS_KEY, REDIS_TTL);
      await redis.expire(REDIS_META_KEY, REDIS_TTL);
    }
  } catch {
    // Non-critical — cache will still work until current TTL expires
  }
}

/**
 * Fetch alarms with retry logic. Tries up to RETRY_ATTEMPTS times.
 * On failure, extends existing Redis cache TTL so data never disappears.
 */
export async function fetchAndCacheAlarms(): Promise<boolean> {
  if (!ALARM_API_KEY) {
    console.warn('[ALARM-BG] No API key configured, skipping fetch');
    return false;
  }

  if (!(await acquireFetchLeaderLock())) {
    return true;
  }

  // Try up to RETRY_ATTEMPTS times with backoff
  for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
    const data = await singleFetch();
    if (data) {
      // Compute etag for change detection
      const json = JSON.stringify(data);
      const etag = `"${crypto.createHash('md5').update(json).digest('hex').slice(0, 16)}"`;

      // Store in Redis with TTL
      await redisSet(REDIS_KEY, data, REDIS_TTL);
      await redisSet(REDIS_META_KEY, new Date().toISOString(), REDIS_TTL);

      // Broadcast to SSE clients only when data actually changed
      if (etag !== lastETag) {
        lastETag = etag;
        broadcastSSE({ type: 'alarm_update', data });
        console.log(`[ALARM-BG] Cached ${data.length} alarms in Redis (changed, attempt ${attempt + 1})`);
      }

      return true;
    }

    // Wait before retry (except on last attempt)
    if (attempt < RETRY_ATTEMPTS - 1) {
      await new Promise((r) => setTimeout(r, RETRY_DELAYS[attempt]));
    }
  }

  // All retries failed — extend existing cache TTL so alarms never disappear
  await extendCacheTTL();
  return false;
}

/**
 * Start the background alarm fetcher interval.
 */
export function startAlarmFetcher() {
  if (intervalId) return;

  console.log('[ALARM-BG] Starting background fetcher');

  (async () => {
    // Check if Redis already has data (warm start from previous run)
    const existing = await redisGet(REDIS_KEY);
    if (existing && Array.isArray(existing) && existing.length > 0) {
      console.log(`[ALARM-BG] Redis warm start: ${existing.length} alarms already cached`);
    }

    // Initial fetch with retries — API often returns 401 intermittently.
    // Do not trust fetchAndCacheAlarms() alone: another PM2 worker may hold the leader lock.
    for (let attempt = 0; attempt < 10; attempt++) {
      await fetchAndCacheAlarms();
      const after = await redisGet(REDIS_KEY);
      if (after && Array.isArray(after) && after.length > 0) {
        console.log(`[ALARM-BG] Initial fetch succeeded on attempt ${attempt + 1}`);
        return;
      }
      await new Promise((r) => setTimeout(r, 2000 * (attempt + 1)));
    }
    console.warn('[ALARM-BG] Initial fetch failed after 10 attempts — will keep retrying via interval');
  })();

  intervalId = setInterval(fetchAndCacheAlarms, FETCH_INTERVAL);
}

/**
 * Stop the background alarm fetcher.
 */
export function stopAlarmFetcher() {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
    console.log('[ALARM-BG] Stopped background fetcher');
  }
}

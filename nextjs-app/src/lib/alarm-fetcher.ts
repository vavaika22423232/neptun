/**
 * Background alarm fetcher for Node.js server side.
 *
 * In the Flask version, this ran as a background thread.
 * In Next.js, the cache layer in API routes handles freshness.
 * This module provides a warm-up function to pre-populate the cache
 * on server start, plus an optional interval-based fetcher for cron jobs.
 *
 * The actual alarm fetching logic is in /api/alarms/all/route.ts
 * which handles TTL caching, ETag, and stale data fallback.
 */

import { cache } from './cache';

const ALARM_API_BASE = 'https://api.ukrainealarm.com/api/v3';
const ALARM_API_KEY = process.env.ALARM_API_KEY || process.env.ALARMS_API_KEY || '';
const FETCH_INTERVAL = 30_000; // 30 seconds
const CACHE_KEY = 'alarms_all';
const CACHE_TTL = 30_000;

let intervalId: ReturnType<typeof setInterval> | null = null;

/**
 * Fetch alarms directly from the Ukraine Alarm API
 * and populate the cache.
 */
export async function fetchAndCacheAlarms(): Promise<boolean> {
  if (!ALARM_API_KEY) {
    console.warn('[ALARM-BG] No API key configured, skipping fetch');
    return false;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10_000);

    const response = await fetch(`${ALARM_API_BASE}/alerts`, {
      headers: { Authorization: ALARM_API_KEY },
      signal: controller.signal,
      cache: 'no-store',
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn(`[ALARM-BG] API returned ${response.status}`);
      return false;
    }

    const data = await response.json();
    if (Array.isArray(data)) {
      cache.set(CACHE_KEY, data, CACHE_TTL);
      console.log(`[ALARM-BG] Cached ${data.length} alarms`);
      return true;
    }
  } catch (err) {
    console.warn('[ALARM-BG] Fetch failed:', err);
  }

  return false;
}

/**
 * Start the background alarm fetcher interval.
 * Call this from instrumentation.ts or server startup.
 */
export function startAlarmFetcher() {
  if (intervalId) return;

  console.log('[ALARM-BG] Starting background fetcher');

  // Initial fetch
  fetchAndCacheAlarms();

  // Set up interval
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

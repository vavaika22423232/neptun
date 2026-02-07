import { cache, withETag, generateETag } from '@/lib/cache';
import type { Alarm } from '@/types';

const ALARM_API_BASE = 'https://api.ukrainealarm.com/api/v3';
const ALARM_API_KEY = process.env.ALARM_API_KEY || process.env.ALARMS_API_KEY || '';
const CACHE_KEY = 'alarms_all';
const CACHE_TTL = 30_000; // 30 seconds
const STALE_TTL = 7200_000; // 2 hours (serve stale data if API is down)

async function fetchAlarmsFromApi(): Promise<Alarm[] | null> {
  if (!ALARM_API_KEY) {
    console.warn('[ALARM] No API key configured');
    return null;
  }

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10_000);

      const response = await fetch(`${ALARM_API_BASE}/alerts`, {
        headers: { Authorization: ALARM_API_KEY },
        signal: controller.signal,
        cache: 'no-store',
      });
      clearTimeout(timeoutId);

      if (response.status === 401) {
        console.error('[ALARM] API returned 401 - key may be expired');
        return null;
      }

      if (!response.ok) {
        console.warn(`[ALARM] API returned ${response.status} on attempt ${attempt + 1}`);
        continue;
      }

      const data = await response.json();
      if (Array.isArray(data)) return data as Alarm[];
    } catch (err) {
      console.warn(`[ALARM] Fetch attempt ${attempt + 1} failed:`, err);
    }

    // Wait before retry
    if (attempt < 2) await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
  }

  return null;
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // Check cache first
  const { entry, isStale } = cache.getWithStale<Alarm[]>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    // Fresh cache - return with ETag check
    return withETag(entry.data, entry.etag, clientETag);
  }

  // Cache is stale or missing - fetch from API
  const freshData = await fetchAlarmsFromApi();

  if (freshData) {
    // Update cache with fresh data
    const newEntry = cache.set(CACHE_KEY, freshData, CACHE_TTL);
    return withETag(newEntry.data, newEntry.etag, clientETag);
  }

  // API failed - serve stale data if available
  if (entry) {
    console.log('[ALARM] Serving stale data (API unavailable)');
    return withETag(entry.data, entry.etag, clientETag);
  }

  // No cache, no API - return empty
  return new Response(JSON.stringify([]), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

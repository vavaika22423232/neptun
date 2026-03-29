/**
 * Shared alarm list loading for /api/alarms/all and /api/alarms/proxy.
 * Single source of truth: Redis (alarm-fetcher) with cold-start API fallback.
 */

import { redisGetWithMeta, redisSet } from '@/lib/redis';
import { generateETag } from '@/lib/cache';
import type { Alarm } from '@/types';

const ALARM_API_BASE = 'https://api.ukrainealarm.com/api/v3';
const REDIS_KEY = 'alarms:all';
const REDIS_META_KEY = 'alarms:last_updated';
/** Max age (seconds) before redisGetWithMeta treats key as unusable — matches former /api/alarms/all */
const REDIS_STALE_AFTER_S = 600;
const COLD_FETCH_WRITE_TTL = 600;

export type LoadedAlarms = {
  data: Alarm[];
  etag: string;
  ageSeconds: number;
  rawJson?: string;
};

function alarmApiKey(): string {
  return process.env.ALARM_API_KEY || process.env.ALARMS_API_KEY || '';
}

/**
 * Load current alarms from Redis or direct API (cold start).
 * Returns null only when no data is available anywhere.
 */
export async function loadAlarms(): Promise<LoadedAlarms | null> {
  const { data, age, raw } = await redisGetWithMeta<Alarm[]>(REDIS_KEY, REDIS_STALE_AFTER_S);

  if (data && Array.isArray(data) && data.length > 0) {
    return {
      data,
      etag: generateETag(data),
      ageSeconds: Math.round(age),
      rawJson: raw ?? undefined,
    };
  }

  const key = alarmApiKey();
  if (!key) return null;

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5_000);
      const response = await fetch(`${ALARM_API_BASE}/alerts`, {
        headers: { Authorization: key },
        signal: controller.signal,
        cache: 'no-store',
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const fetched = (await response.json()) as unknown;
        if (Array.isArray(fetched)) {
          await redisSet(REDIS_KEY, fetched, COLD_FETCH_WRITE_TTL);
          await redisSet(REDIS_META_KEY, new Date().toISOString(), COLD_FETCH_WRITE_TTL);
          return {
            data: fetched as Alarm[],
            etag: generateETag(fetched),
            ageSeconds: 0,
          };
        }
      }
    } catch {
      /* retry */
    }
    if (attempt < 2) await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
  }

  return null;
}

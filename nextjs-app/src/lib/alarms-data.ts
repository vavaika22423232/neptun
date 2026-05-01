/**
 * Shared alarm list loading for /api/alarms/all and /api/alarms/proxy.
 * Single source of truth: Redis (alarm-fetcher) with cold-start API fallback.
 */

import { readFileSync } from 'fs';
import path from 'path';
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

/* ── Dev-only payload shaping (must match GET /api/alarms/all) ── */

type DevRaionFeatureCollection = {
  features?: Array<{
    properties?: {
      rayon?: unknown;
    } | null;
  }>;
};

let cachedDevRaionNames: string[] | null = null;

function loadDevRaionNames(): string[] {
  if (cachedDevRaionNames) return cachedDevRaionNames;
  try {
    const file = path.join(process.cwd(), 'public', 'ukraine_raions_2020.geojson');
    const parsed = JSON.parse(readFileSync(file, 'utf8')) as DevRaionFeatureCollection;
    cachedDevRaionNames = (parsed.features ?? [])
      .map((feature) => String(feature.properties?.rayon ?? '').trim())
      .filter((name) => name.length > 0);
  } catch (error) {
    console.warn('[ALARM-DEV] Failed to load raion GeoJSON names:', error);
    cachedDevRaionNames = [];
  }
  return cachedDevRaionNames;
}

/** Same body shaping as `app/api/alarms/all/route.ts` (district flood in dev). */
export function withDevAllDistrictAlarms(alarms: Alarm[]): Alarm[] {
  if (process.env.NODE_ENV === 'production') return alarms;
  if (process.env.DEV_ALL_DISTRICT_ALARMS !== '1') return alarms;

  const now = new Date().toISOString();
  const devDistrictAlarms: Alarm[] = loadDevRaionNames()
    .filter((_, index) => index % 2 === 0)
    .map((regionName, index) => ({
      regionId: `dev-raion-${index}`,
      regionType: 'District',
      regionName,
      activeAlerts: [{ type: 'AIR', lastUpdate: now }],
    }));

  const devDistrictNames = new Set(
    devDistrictAlarms
      .map((alarm) => alarm.regionName)
      .filter((regionName): regionName is string => typeof regionName === 'string'),
  );
  const withoutExistingDevDistricts = alarms.filter(
    (alarm) => !(alarm.regionType === 'District' && alarm.regionName && devDistrictNames.has(alarm.regionName)),
  );
  return [...withoutExistingDevDistricts, ...devDistrictAlarms];
}

/**
 * Cached alarms for first paint (App Router SSR). Matches GET /api/alarms/all JSON + ETag rules.
 */
export async function getInitialAlarmsSnapshot(): Promise<{
  alarms: Alarm[];
  etag: string | null;
}> {
  const loaded = await loadAlarms();
  if (!loaded) {
    return { alarms: withDevAllDistrictAlarms([]), etag: null };
  }
  const data = withDevAllDistrictAlarms(loaded.data);
  const etag = data === loaded.data ? loaded.etag : generateETag(data);
  return { alarms: data, etag };
}

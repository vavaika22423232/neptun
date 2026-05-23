/**
 * Server-side alert event journal (Redis). Populated from alarm-fetcher diffs.
 */

import { getRedis } from '@/lib/redis';
import { randomUUID } from 'crypto';
import type { Alarm } from '@/types';

export type AlertEventRecord = {
  id: string;
  type: string;
  regionId: string;
  cityId: string | null;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  startedAt: string;
  endedAt: string | null;
  createdAt: string;
  updatedAt: string;
  metadataJson: Record<string, unknown>;
};

const EVENT_PREFIX = 'monetization:alert_event:';
const REGION_INDEX = 'monetization:alert_events:by_region:';
const GLOBAL_INDEX = 'monetization:alert_events:global';
const OPEN_PREFIX = 'monetization:alert_open:';
const MAX_EVENTS_PER_REGION = 500;

function eventKey(id: string) {
  return `${EVENT_PREFIX}${id}`;
}

function regionIndex(regionId: string) {
  return `${REGION_INDEX}${regionId}`;
}

function openKey(regionId: string, alertType: string) {
  return `${OPEN_PREFIX}${regionId}:${alertType}`;
}

function alertTypeLabel(type: string): string {
  const t = type.toLowerCase();
  if (t.includes('air') || t === 'airalarm') return 'air_alarm';
  if (t.includes('shahed') || t.includes('drone')) return 'shahed';
  if (t.includes('ballistic')) return 'ballistic';
  if (t.includes('missile') || t.includes('raketa')) return 'missile';
  if (t.includes('avia') || t.includes('mig')) return 'aviation';
  if (t.includes('artillery') || t.includes('obstril')) return 'explosion';
  if (t.includes('clear') || t.includes('vidboi')) return 'all_clear';
  return 'air_alarm';
}

function severityForType(type: string): AlertEventRecord['severity'] {
  const t = alertTypeLabel(type);
  if (t === 'ballistic' || t === 'missile') return 'critical';
  if (t === 'shahed' || t === 'air_alarm') return 'high';
  if (t === 'all_clear') return 'low';
  return 'medium';
}

async function persistEvent(rec: AlertEventRecord): Promise<void> {
  await getRedis().hset(eventKey(rec.id), {
    id: rec.id,
    type: rec.type,
    regionId: rec.regionId,
    cityId: rec.cityId ?? '',
    title: rec.title,
    description: rec.description,
    severity: rec.severity,
    source: rec.source,
    startedAt: rec.startedAt,
    endedAt: rec.endedAt ?? '',
    createdAt: rec.createdAt,
    updatedAt: rec.updatedAt,
    metadataJson: JSON.stringify(rec.metadataJson),
  });
  await getRedis().zadd(regionIndex(rec.regionId), Date.parse(rec.startedAt), rec.id);
  await getRedis().zadd(GLOBAL_INDEX, Date.parse(rec.startedAt), rec.id);
  await getRedis().zremrangebyrank(regionIndex(rec.regionId), 0, -(MAX_EVENTS_PER_REGION + 1));
}

function parseEvent(raw: Record<string, string>): AlertEventRecord {
  return {
    id: raw.id,
    type: raw.type,
    regionId: raw.regionId,
    cityId: raw.cityId || null,
    title: raw.title,
    description: raw.description,
    severity: (raw.severity as AlertEventRecord['severity']) || 'medium',
    source: raw.source,
    startedAt: raw.startedAt,
    endedAt: raw.endedAt || null,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
    metadataJson: JSON.parse(raw.metadataJson || '{}') as Record<string, unknown>,
  };
}

/**
 * Compare alarm snapshots and append start/end events.
 */
export async function recordAlarmSnapshotDiff(alarms: Alarm[]): Promise<void> {
  const redis = getRedis();
  const activeNow = new Map<string, { regionId: string; regionName: string; types: string[] }>();

  for (const a of alarms) {
    if (!a.activeAlerts?.length) continue;
    const types = a.activeAlerts.map((x) => alertTypeLabel(x.type));
    activeNow.set(a.regionId, {
      regionId: a.regionId,
      regionName: a.regionName ?? a.regionId,
      types,
    });
  }

  const prevKeys = await redis.keys(`${OPEN_PREFIX}*`);
  const prevOpen = new Set(prevKeys.map((k) => k.replace(OPEN_PREFIX, '')));

  const nowOpen = new Set<string>();

  for (const [, info] of activeNow) {
    for (const alertType of info.types) {
      const key = `${info.regionId}:${alertType}`;
      nowOpen.add(key);
      if (prevOpen.has(key)) continue;

      const id = randomUUID();
      const now = new Date().toISOString();
      const rec: AlertEventRecord = {
        id,
        type: alertType,
        regionId: info.regionId,
        cityId: null,
        title: `Тривога: ${info.regionName}`,
        description: `За наявними даними — ${alertType}. Інформація оновлюється.`,
        severity: severityForType(alertType),
        source: 'ukraine_alarm',
        startedAt: now,
        endedAt: null,
        createdAt: now,
        updatedAt: now,
        metadataJson: { regionName: info.regionName },
      };
      await persistEvent(rec);
      await redis.set(openKey(info.regionId, alertType), id, 'EX', 90 * 24 * 3600);
    }
  }

  for (const key of prevOpen) {
    if (nowOpen.has(key)) continue;
    const [regionId, alertType] = key.split(':');
    const openId = await redis.get(openKey(regionId, alertType));
    if (openId) {
      const raw = await redis.hgetall(eventKey(openId));
      if (raw?.id) {
        const ended = new Date().toISOString();
        await redis.hset(eventKey(openId), { endedAt: ended, updatedAt: ended });
      }
      await redis.del(openKey(regionId, alertType));
    }
  }
}

export async function listAlertEvents(opts: {
  regionId?: string;
  fromIso: string;
  toIso?: string;
  type?: string;
  limit?: number;
}): Promise<AlertEventRecord[]> {
  const fromMs = Date.parse(opts.fromIso);
  const toMs = opts.toIso ? Date.parse(opts.toIso) : Date.now();
  const index = opts.regionId ? regionIndex(opts.regionId) : GLOBAL_INDEX;
  const ids = await getRedis().zrangebyscore(index, fromMs, toMs);
  const slice = ids.slice(-(opts.limit ?? 200));
  const out: AlertEventRecord[] = [];

  for (const id of slice.reverse()) {
    const raw = await getRedis().hgetall(eventKey(id));
    if (!raw?.id) continue;
    const ev = parseEvent(raw);
    if (opts.type && ev.type !== opts.type) continue;
    out.push(ev);
  }
  return out;
}

export async function getAlertEvent(id: string): Promise<AlertEventRecord | null> {
  const raw = await getRedis().hgetall(eventKey(id));
  if (!raw?.id) return null;
  return parseEvent(raw);
}

export async function getCurrentAlertsFromRedis(): Promise<Alarm[]> {
  const { redisGet } = await import('@/lib/redis');
  const data = await redisGet<Alarm[]>('alarms:all');
  return Array.isArray(data) ? data : [];
}

export async function aggregateRegionStatsDaily(
  regionId: string,
  fromIso: string,
  toIso: string,
): Promise<
  Array<{
    regionId: string;
    date: string;
    totalAlerts: number;
    totalAlarmMinutes: number;
    shahedEvents: number;
    missileEvents: number;
    ballisticEvents: number;
    avgDurationMinutes: number;
    maxDurationMinutes: number;
  }>
> {
  const events = await listAlertEvents({ regionId, fromIso, toIso, limit: 1000 });
  const byDate = new Map<string, typeof events>();

  for (const ev of events) {
    const d = ev.startedAt.slice(0, 10);
    if (!byDate.has(d)) byDate.set(d, []);
    byDate.get(d)!.push(ev);
  }

  return [...byDate.entries()].map(([date, dayEvents]) => {
    let totalMinutes = 0;
    let maxDur = 0;
    let shahed = 0;
    let missile = 0;
    let ballistic = 0;

    for (const ev of dayEvents) {
      if (ev.type === 'shahed') shahed += 1;
      if (ev.type === 'missile') missile += 1;
      if (ev.type === 'ballistic') ballistic += 1;
      if (ev.endedAt) {
        const mins = (Date.parse(ev.endedAt) - Date.parse(ev.startedAt)) / 60_000;
        if (mins > 0) {
          totalMinutes += mins;
          maxDur = Math.max(maxDur, mins);
        }
      }
    }

    const count = dayEvents.length;
    return {
      regionId,
      date,
      totalAlerts: count,
      totalAlarmMinutes: Math.round(totalMinutes),
      shahedEvents: shahed,
      missileEvents: missile,
      ballisticEvents: ballistic,
      avgDurationMinutes: count > 0 ? Math.round(totalMinutes / count) : 0,
      maxDurationMinutes: Math.round(maxDur),
    };
  });
}

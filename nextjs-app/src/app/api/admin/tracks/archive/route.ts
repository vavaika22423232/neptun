/**
 * P4-E: Historical track archive
 *
 * GET  /api/admin/tracks/archive          — list archived track summaries
 * POST /api/admin/tracks/archive/snapshot — write current tracker state to archive
 *
 * Archive entries are stored as a Redis sorted set keyed by timestamp so they
 * can be queried chronologically.  Each entry is a compact JSON snapshot of all
 * active targets at that moment, useful for post-incident analysis.
 *
 * If NEPTUN_POSTGRES_URL is set, entries are ALSO written to a PostgreSQL table
 * `tracker_archive` (created on first write).  When Postgres is unavailable,
 * the system falls back to Redis-only storage.
 */
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { getRedis } from '@/lib/redis';

export const dynamic = 'force-dynamic';

const ARCHIVE_ZSET_KEY = 'tracker:archive:snapshots';
const ARCHIVE_MAX_ENTRIES = 500;

type ArchiveEntry = {
  ts: number;
  active_count: number;
  threat_type_counts: Record<string, number>;
  avg_tqi: number | null;
  targets: Array<{
    id: string;
    threat_type: string;
    lat: number;
    lng: number;
    lifecycle: string;
    confidence: number;
    tqi?: number;
  }>;
};

async function tryWritePostgres(entry: ArchiveEntry): Promise<boolean> {
  const pgUrl = process.env.NEPTUN_POSTGRES_URL;
  if (!pgUrl) return false;

  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-var-requires
    const pgModule: { default?: unknown } = await (new Function('m', 'return import(m)')('postgres') as Promise<{ default?: unknown }>).catch(() => null as never);
    if (!pgModule) return false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const postgres = (pgModule.default ?? pgModule) as (url: string, opts: Record<string, unknown>) => any;
    const sql = postgres(pgUrl, { max: 2, idle_timeout: 10 });

    await sql`
      CREATE TABLE IF NOT EXISTS tracker_archive (
        id         BIGSERIAL PRIMARY KEY,
        ts         TIMESTAMPTZ NOT NULL,
        snapshot   JSONB NOT NULL
      )
    `;
    await sql`
      INSERT INTO tracker_archive (ts, snapshot)
      VALUES (to_timestamp(${entry.ts / 1000}), ${sql.json(entry)})
    `;
    await sql.end();
    return true;
  } catch {
    return false;
  }
}

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const limit = Math.min(100, parseInt(url.searchParams.get('limit') ?? '50', 10) || 50);

  try {
    const redis = getRedis();
    const raw = await redis.zrevrange(ARCHIVE_ZSET_KEY, 0, limit - 1, 'WITHSCORES');
    const entries: ArchiveEntry[] = [];

    for (let i = 0; i < raw.length; i += 2) {
      try {
        const entry = JSON.parse(raw[i]!) as ArchiveEntry;
        entries.push(entry);
      } catch { /* skip corrupt entries */ }
    }

    return NextResponse.json({
      count: entries.length,
      entries: entries.map((e) => ({
        ts: e.ts,
        active_count: e.active_count,
        threat_type_counts: e.threat_type_counts,
        avg_tqi: e.avg_tqi,
      })),
    });
  } catch {
    return NextResponse.json({ count: 0, entries: [], error: 'redis_unavailable' });
  }
}

export async function POST() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const { initTargetStore, syncTargetStoreFromRedis, getTrackedTargetRecords } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const records = getTrackedTargetRecords();
  const nowMs = Date.now();

  const active = records.filter((r) => {
    const lc = r.target_lifecycle_state as string | undefined;
    return lc === 'CONFIRMED' || lc === 'TRACKING' || lc === 'DETECTED';
  });

  const threatTypeCounts: Record<string, number> = {};
  for (const r of active) {
    const tt = (r.threat_type as string) || 'unknown';
    threatTypeCounts[tt] = (threatTypeCounts[tt] ?? 0) + 1;
  }

  const tqiValues = active
    .map((r) => (typeof r.tqi === 'number' ? r.tqi : null))
    .filter((v): v is number => v !== null);
  const avgTqi = tqiValues.length > 0
    ? Math.round(tqiValues.reduce((s, v) => s + v, 0) / tqiValues.length)
    : null;

  const entry: ArchiveEntry = {
    ts: nowMs,
    active_count: active.length,
    threat_type_counts: threatTypeCounts,
    avg_tqi: avgTqi,
    targets: active.slice(0, 200).map((r) => ({
      id: r.id as string,
      threat_type: r.threat_type as string,
      lat: r.lat as number,
      lng: r.lng as number,
      lifecycle: (r.target_lifecycle_state as string) || 'UNKNOWN',
      confidence: (r.target_confidence as number) ?? 0,
      tqi: r.tqi as number | undefined,
    })),
  };

  let storedInPostgres = false;

  try {
    const redis = getRedis();
    await redis.zadd(ARCHIVE_ZSET_KEY, nowMs, JSON.stringify(entry));
    // Trim to max entries
    const total = await redis.zcard(ARCHIVE_ZSET_KEY);
    if (total > ARCHIVE_MAX_ENTRIES) {
      await redis.zremrangebyrank(ARCHIVE_ZSET_KEY, 0, total - ARCHIVE_MAX_ENTRIES - 1);
    }
  } catch {
    return NextResponse.json({ error: 'Failed to write to Redis archive' }, { status: 500 });
  }

  storedInPostgres = await tryWritePostgres(entry);

  return NextResponse.json({
    ok: true,
    ts: nowMs,
    active_count: active.length,
    stored_in_postgres: storedInPostgres,
  });
}

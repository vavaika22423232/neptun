/**
 * P4-D: POST /api/admin/tracks/override
 *
 * Operator override API — allows admins to manually adjust any tracked target's
 * properties.  All overrides are written to a rolling audit log in Redis so
 * every operator action is traceable.
 *
 * Body (JSON):
 *   {
 *     "target_id": "trk_shahed_1234",
 *     "updates": {
 *       "lat": 48.5, "lng": 32.1,           // reposition
 *       "threat_type": "ballistic",          // reclassify
 *       "speed_kmh": 800,
 *       "course_bearing": 270,
 *       "lifecycle": "LOST",                 // mark as lost/destroyed
 *       "note": "Ground truth from OSINT"    // audit note
 *     }
 *   }
 *
 * Returns:
 *   { ok: true, target_id, applied_at }
 */
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { getRedis } from '@/lib/redis';

export const dynamic = 'force-dynamic';

const AUDIT_LOG_KEY = 'tracker:overrides:audit';
const AUDIT_LOG_MAX = 200;

type LifecycleState = 'LOST' | 'DESTROYED' | 'STALE' | 'REJECTED';
const LIFECYCLE_STATES: LifecycleState[] = ['LOST', 'DESTROYED', 'STALE', 'REJECTED'];

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const targetId = typeof body.target_id === 'string' ? body.target_id.trim() : '';
  if (!targetId) {
    return NextResponse.json({ error: 'Missing target_id' }, { status: 400 });
  }

  const updates = (body.updates && typeof body.updates === 'object')
    ? body.updates as Record<string, unknown>
    : {};

  const { initTargetStore, syncTargetStoreFromRedis, updateTrackedTarget, markTrackedTargetLifecycle } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const appliedAt = Date.now();
  let ok = false;

  // Handle lifecycle change separately
  const lifecycle = typeof updates.lifecycle === 'string' ? updates.lifecycle : null;
  if (lifecycle && LIFECYCLE_STATES.includes(lifecycle as LifecycleState)) {
    ok = await markTrackedTargetLifecycle(targetId, lifecycle as LifecycleState);
  } else {
    ok = await updateTrackedTarget(targetId, updates);
  }

  if (!ok) {
    return NextResponse.json({ error: `Track not found: ${targetId}` }, { status: 404 });
  }

  // Persist audit log entry to Redis
  try {
    const redis = getRedis();
    const entry = JSON.stringify({
      target_id: targetId,
      updates,
      applied_at: appliedAt,
      note: typeof updates.note === 'string' ? updates.note : undefined,
    });
    await redis.lpush(AUDIT_LOG_KEY, entry);
    await redis.ltrim(AUDIT_LOG_KEY, 0, AUDIT_LOG_MAX - 1);
  } catch {
    /* Audit log write failure is non-fatal */
  }

  return NextResponse.json({ ok: true, target_id: targetId, applied_at: appliedAt });
}

/** GET /api/admin/tracks/override — fetch recent audit log */
export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const redis = getRedis();
    const raw = await redis.lrange(AUDIT_LOG_KEY, 0, AUDIT_LOG_MAX - 1);
    const entries = raw.map((s) => {
      try { return JSON.parse(s); } catch { return null; }
    }).filter(Boolean);
    return NextResponse.json({ entries, count: entries.length });
  } catch {
    return NextResponse.json({ entries: [], count: 0, error: 'redis_unavailable' });
  }
}

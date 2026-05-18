import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

/**
 * P4-E: GET /api/admin/tracks/replay?id=<track_id>
 *
 * Returns a step-by-step replay of a tracked target's history:
 * - Each accepted/rejected observation with its association score
 * - EKF state at each step (position, speed, bearing, sigma)
 * - Lifecycle transitions
 * - Publication decisions
 *
 * Useful for debugging false associations, impossible movements, and
 * understanding why a target was or wasn't published.
 */
export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const trackId = url.searchParams.get('id')?.trim();
  if (!trackId) {
    return NextResponse.json({ error: 'Missing ?id= parameter' }, { status: 400 });
  }

  const { getTrackedTargetRecords, initTargetStore, syncTargetStoreFromRedis } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const records = getTrackedTargetRecords();
  const target = records.find((r) => r.id === trackId || r.track_id === trackId);
  if (!target) {
    return NextResponse.json({ error: `Track not found: ${trackId}` }, { status: 404 });
  }

  const history = Array.isArray(target.observations) ? target.observations : [];
  const rejected = Array.isArray(target.rejected_observations) ? target.rejected_observations : [];

  // Combine and sort all events by timestamp
  type EventEntry = Record<string, unknown> & { accepted: boolean };
  const allEvents: EventEntry[] = [
    ...history.map((h: Record<string, unknown>): EventEntry => ({ ...h, accepted: true })),
    ...rejected.map((h: Record<string, unknown>): EventEntry => ({ ...h, accepted: false })),
  ].sort((a, b) => Number(a['ts']) - Number(b['ts']));

  return NextResponse.json({
    id: target.id,
    track_id: target.track_id,
    threat_type: target.threat_type,
    place: target.place,
    region: target.region,
    lifecycle_state: target.target_lifecycle_state,
    confidence: target.target_confidence,
    tqi: target.tqi,
    first_seen: target.created_at_epoch,
    last_seen: target.last_update_epoch,
    source_count: target.source_count,
    upstream_track_ids: target.upstream_track_ids,
    formation_id: target.formation_id,
    altitude_mode: target.altitude_mode,
    coastal_transition: target.coastal_transition,
    trajectory_confidence: target.trajectory_confidence,
    ekf_snapshot: target.ekf,
    publication_history: target.publication_history ?? [],
    last_association: target.last_association,
    // Full event replay
    events: allEvents.map((h) => ({
      ts: h['ts'],
      lat: h['lat'],
      lng: h['lng'],
      source: h['source'],
      accepted: h.accepted,
      reason: h['reason'],
      confidence: h['confidence'],
    })),
    event_count: allEvents.length,
    accepted_count: allEvents.filter((e) => e.accepted).length,
    rejected_count: allEvents.filter((e) => !e.accepted).length,
  });
}

/**
 * P5-D: POST /api/admin/tracks/feedback
 *
 * Accept confirmed trajectory accuracy feedback (actual impact/landing location).
 * This allows the tracker to:
 *   1. Record the prediction error on the target for dashboards.
 *   2. Apply a small EMA correction to the per-channel geo-bias table so future
 *      reports from the same source are shifted toward the confirmed location.
 *
 * Body (JSON):
 *   {
 *     "target_id": "trk_shahed_1234",
 *     "actual_lat": 48.5123,
 *     "actual_lng": 32.1456,
 *     "note": "Confirmed by OSINT — crater at grid 48.5/32.1"
 *   }
 */
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

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
  const actualLat = typeof body.actual_lat === 'number' ? body.actual_lat : Number(body.actual_lat);
  const actualLng = typeof body.actual_lng === 'number' ? body.actual_lng : Number(body.actual_lng);

  if (!targetId) return NextResponse.json({ error: 'Missing target_id' }, { status: 400 });
  if (!Number.isFinite(actualLat) || !Number.isFinite(actualLng)) {
    return NextResponse.json({ error: 'Invalid actual_lat or actual_lng' }, { status: 400 });
  }

  const { initTargetStore, syncTargetStoreFromRedis, recordTrajectoryFeedbackForTarget } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const ok = await recordTrajectoryFeedbackForTarget(targetId, actualLat, actualLng);
  if (!ok) {
    return NextResponse.json({ error: `Track not found: ${targetId}` }, { status: 404 });
  }

  return NextResponse.json({
    ok: true,
    target_id: targetId,
    actual_lat: actualLat,
    actual_lng: actualLng,
    recorded_at: Date.now(),
  });
}

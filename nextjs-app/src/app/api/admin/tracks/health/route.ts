import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

/**
 * P4-B: GET /api/admin/tracks/health
 *
 * Returns a concise health summary of the TrackedTargetEngine:
 * - active/stale/lost/total counts per threat type
 * - TQI distribution (p25/p50/p75)
 * - EKF health (avg singularSkipCount)
 * - formation count
 * - average trajectory confidence
 * - recent publication decisions breakdown
 */
export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const { getTrackedTargetRecords, initTargetStore, syncTargetStoreFromRedis } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const records = getTrackedTargetRecords();
  const nowMs = Date.now();

  // ── Lifecycle counts ──────────────────────────────────────────────────────
  const byLifecycle: Record<string, number> = {};
  const byThreatType: Record<string, { active: number; stale: number; lost: number }> = {};

  for (const r of records) {
    const state = (r.target_lifecycle_state as string) || 'unknown';
    byLifecycle[state] = (byLifecycle[state] ?? 0) + 1;

    const tt = (r.threat_type as string) || 'unknown';
    if (!byThreatType[tt]) byThreatType[tt] = { active: 0, stale: 0, lost: 0 };
    if (state === 'CONFIRMED' || state === 'TRACKING' || state === 'DETECTED') {
      byThreatType[tt].active++;
    } else if (state === 'STALE') {
      byThreatType[tt].stale++;
    } else if (state === 'LOST' || state === 'DESTROYED') {
      byThreatType[tt].lost++;
    }
  }

  // ── TQI distribution ──────────────────────────────────────────────────────
  const tqiValues = records
    .map((r) => typeof r.tqi === 'number' ? r.tqi : null)
    .filter((v): v is number => v !== null)
    .sort((a, b) => a - b);

  function percentile(arr: number[], p: number): number | null {
    if (arr.length === 0) return null;
    const idx = Math.floor(arr.length * p);
    return arr[Math.min(idx, arr.length - 1)] ?? null;
  }

  const tqiP25 = percentile(tqiValues, 0.25);
  const tqiP50 = percentile(tqiValues, 0.5);
  const tqiP75 = percentile(tqiValues, 0.75);

  // ── EKF health ────────────────────────────────────────────────────────────
  const ekfRecords = records.filter((r) => r.ekf != null);
  const avgSingularSkips = ekfRecords.length > 0
    ? ekfRecords.reduce((sum, r) => {
        const ekf = r.ekf as Record<string, unknown> | undefined;
        return sum + (typeof ekf?.singularSkipCount === 'number' ? ekf.singularSkipCount : 0);
      }, 0) / ekfRecords.length
    : null;

  // ── Formation count ───────────────────────────────────────────────────────
  const formationIds = new Set(
    records
      .map((r) => r.formation_id as string | undefined)
      .filter((id): id is string => typeof id === 'string' && id.length > 0),
  );

  // ── Trajectory confidence ─────────────────────────────────────────────────
  const trajConfs = records
    .map((r) => typeof r.trajectory_confidence === 'number' ? r.trajectory_confidence : null)
    .filter((v): v is number => v !== null);
  const avgTrajConf = trajConfs.length > 0
    ? trajConfs.reduce((s, v) => s + v, 0) / trajConfs.length
    : null;

  // ── Publication history ───────────────────────────────────────────────────
  let pubPublic = 0;
  let pubAdmin = 0;
  let pubRejected = 0;
  for (const r of records) {
    const hist = r.publication_history as Array<{ public: boolean; classification: string }> | undefined;
    if (!hist) continue;
    for (const h of hist) {
      if (h.public) pubPublic++;
      else if (h.classification === 'REJECTED') pubRejected++;
      else pubAdmin++;
    }
  }

  // ── Altitude mode breakdown ───────────────────────────────────────────────
  const altitudeModes: Record<string, number> = {};
  for (const r of records) {
    const am = (r.altitude_mode as string) || 'unknown';
    altitudeModes[am] = (altitudeModes[am] ?? 0) + 1;
  }

  return NextResponse.json({
    generated_at: new Date(nowMs).toISOString(),
    total_tracks: records.length,
    by_lifecycle: byLifecycle,
    by_threat_type: byThreatType,
    tqi: {
      count: tqiValues.length,
      p25: tqiP25,
      p50: tqiP50,
      p75: tqiP75,
    },
    ekf: {
      tracks_with_ekf: ekfRecords.length,
      avg_singular_skip_count: avgSingularSkips != null ? Math.round(avgSingularSkips * 100) / 100 : null,
    },
    formations: {
      count: formationIds.size,
      ids: Array.from(formationIds),
    },
    trajectory: {
      avg_confidence: avgTrajConf != null ? Math.round(avgTrajConf * 1000) / 1000 : null,
    },
    publication_history_sample: {
      public: pubPublic,
      admin_only: pubAdmin,
      rejected: pubRejected,
    },
    altitude_modes: altitudeModes,
  });
}

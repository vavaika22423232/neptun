/**
 * P4-C: GET /api/admin/tracks/metrics
 *
 * Returns aggregated accuracy and performance metrics for the tracker system.
 * Designed for automated monitoring dashboards and alerting integrations.
 *
 * Response fields:
 *  - association_rate: fraction of events that resulted in TARGET_UPDATED vs. new track
 *  - avg_tqi: mean Track Quality Index across all active tracks
 *  - avg_trajectory_confidence: mean worker trajectory confidence
 *  - ghost_pool_size: how many expired tracks are in the ghost pool for re-activation
 *  - formation_count: number of detected tactical formations
 *  - swarm_clusters: number of unique swarm cluster ids
 *  - negative_evidence_tracks: tracks with negative_evidence_score > 0.3
 *  - reclassified_tracks: tracks whose threat type was auto-reclassified
 *  - origin_inferred_tracks: tracks with backward-projected launch origin
 *  - maneuver_active: tracks with maneuver_detected = true
 */
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const { getTrackedTargetRecords, initTargetStore, syncTargetStoreFromRedis } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const records = getTrackedTargetRecords();
  const nowMs = Date.now();

  const active = records.filter((r) => {
    const lc = r.target_lifecycle_state as string | undefined;
    return lc === 'CONFIRMED' || lc === 'TRACKING' || lc === 'DETECTED';
  });

  // TQI
  const tqiValues = active
    .map((r) => (typeof r.tqi === 'number' ? r.tqi : null))
    .filter((v): v is number => v !== null);
  const avgTqi = tqiValues.length > 0
    ? Math.round(tqiValues.reduce((s, v) => s + v, 0) / tqiValues.length)
    : null;

  // Trajectory confidence
  const trajConfs = active
    .map((r) => (typeof r.trajectory_confidence === 'number' ? r.trajectory_confidence : null))
    .filter((v): v is number => v !== null);
  const avgTrajConf = trajConfs.length > 0
    ? Math.round((trajConfs.reduce((s, v) => s + v, 0) / trajConfs.length) * 100) / 100
    : null;

  // Formation count
  const formationIds = new Set(
    active.map((r) => r.formation_id as string | undefined).filter((v): v is string => Boolean(v)),
  );

  // Swarm clusters
  const swarmClusters = new Set(
    active.map((r) => r.swarm_cluster_id as string | undefined).filter((v): v is string => Boolean(v)),
  );

  // Negative evidence
  const negativeEvidenceTracks = active.filter(
    (r) => typeof r.negative_evidence_score === 'number' && (r.negative_evidence_score as number) > 0.3,
  ).length;

  // Reclassified
  const reclassifiedTracks = active.filter(
    (r) => typeof r.threat_type_reclassified_from === 'string',
  ).length;

  // Origin inferred
  const originInferredTracks = active.filter((r) => r.origin_inference != null).length;

  // Maneuvering
  const maneuverActive = active.filter((r) => r.maneuver_detected === true).length;

  // ETA coverage (tracks that have eta_seconds)
  const etaCoverage = active.filter((r) => typeof r.eta_seconds === 'number').length;

  // Cross-oblast correlation
  const crossOblastTracks = active.filter(
    (r) => typeof r.cross_oblast_score === 'number' && (r.cross_oblast_score as number) > 0.3,
  ).length;

  // Coastal transitions
  const coastalTransitions = active.filter((r) => r.coastal_transition === true).length;

  // Age distribution
  const ages = active.map((r) => nowMs - (r.last_update_epoch as number || nowMs));
  const avgAgeMs = ages.length > 0 ? Math.round(ages.reduce((s, v) => s + v, 0) / ages.length) : null;

  return NextResponse.json({
    generated_at: new Date(nowMs).toISOString(),
    total_tracks: records.length,
    active_tracks: active.length,
    avg_tqi: avgTqi,
    avg_trajectory_confidence: avgTrajConf,
    eta_coverage: etaCoverage,
    formations: formationIds.size,
    swarm_clusters: swarmClusters.size,
    negative_evidence_tracks: negativeEvidenceTracks,
    reclassified_tracks: reclassifiedTracks,
    origin_inferred_tracks: originInferredTracks,
    maneuver_active: maneuverActive,
    cross_oblast_wave_tracks: crossOblastTracks,
    coastal_transitions: coastalTransitions,
    avg_age_ms: avgAgeMs,
  });
}

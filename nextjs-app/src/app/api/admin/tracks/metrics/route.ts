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

function increment(bucket: Record<string, number>, key: unknown): void {
  const normalized = String(key || 'unknown');
  bucket[normalized] = (bucket[normalized] || 0) + 1;
}

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

  const byObservationQuality: Record<string, number> = {};
  const byTextIntent: Record<string, number> = {};
  const associationReasons: Record<string, number> = {};
  const publicPositionPolicies: Record<string, number> = {};
  const coordinateRoles: Record<string, number> = {};
  const associationScores: number[] = [];
  const uncertaintyValues: number[] = [];
  let targetHintTracks = 0;
  let groupIntentTracks = 0;
  let lossIntentTracks = 0;
  let heldPositionTracks = 0;
  let qualityPenaltyEvents = 0;
  let groupBonusEvents = 0;

  for (const r of active) {
    increment(byObservationQuality, r.last_observation_quality || r.position_source || r.resolve_status);
    increment(byTextIntent, r.last_text_intent);
    const truth = r.tracker_truth as Record<string, unknown> | undefined;
    increment(publicPositionPolicies, truth?.public_position_policy);
    increment(coordinateRoles, truth?.coordinate_role);
    if (typeof truth?.confidence_radius_km === 'number') uncertaintyValues.push(truth.confidence_radius_km);
    if (r.last_observation_quality === 'target_hint') targetHintTracks += 1;
    if (r.last_text_intent === 'group') groupIntentTracks += 1;
    if (r.last_text_intent === 'loss') lossIntentTracks += 1;
    if (r.association_reason === 'associated_position_held') heldPositionTracks += 1;
    const assoc = r.last_association as Record<string, unknown> | undefined;
    if (assoc) {
      increment(associationReasons, assoc.reason);
      if (typeof assoc.score === 'number') associationScores.push(assoc.score);
      if (typeof assoc.quality_penalty === 'number' && assoc.quality_penalty > 0) qualityPenaltyEvents += 1;
      if (typeof assoc.group_bonus === 'number' && assoc.group_bonus > 0) groupBonusEvents += 1;
    }
  }
  const avgAssociationScore = associationScores.length > 0
    ? Math.round((associationScores.reduce((s, v) => s + v, 0) / associationScores.length) * 10) / 10
    : null;
  const avgUncertaintyKm = uncertaintyValues.length > 0
    ? Math.round((uncertaintyValues.reduce((s, v) => s + v, 0) / uncertaintyValues.length) * 10) / 10
    : null;

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
    by_observation_quality: byObservationQuality,
    by_text_intent: byTextIntent,
    by_public_position_policy: publicPositionPolicies,
    by_coordinate_role: coordinateRoles,
    target_hint_tracks: targetHintTracks,
    group_intent_tracks: groupIntentTracks,
    loss_intent_tracks: lossIntentTracks,
    held_position_tracks: heldPositionTracks,
    avg_association_score: avgAssociationScore,
    avg_uncertainty_km: avgUncertaintyKm,
    association_reason_counts: associationReasons,
    quality_penalty_events: qualityPenaltyEvents,
    group_bonus_events: groupBonusEvents,
    avg_age_ms: avgAgeMs,
  });
}

/**
 * One raw store row → Marker (same shape as build-markers .map), for display policy + SSE enrich.
 */
import type { Marker, Trajectory } from '@/types';
import {
  maxSpeedKmhForThreatType,
  sanitizeTrackPoints,
  sanitizeTrajectoryEndpoints,
  sanitizeTrajectoryWaypoints,
} from '@/lib/track-sanitize';

function clampOptionalSpeed(kmh: number | undefined, cap: number): number | undefined {
  if (typeof kmh !== 'number' || !Number.isFinite(kmh) || kmh <= 0) return undefined;
  return Math.min(kmh, cap);
}

function normalizeTrackPointTs(ts: number): number {
  if (!Number.isFinite(ts) || ts <= 0) return Date.now();
  return ts > 10_000_000_000 ? Math.round(ts) : Math.round(ts * 1000);
}

function pointState(value: unknown): Marker['last_observation'] {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const lat = Number(raw.lat);
  const lng = Number(raw.lng);
  const ts = normalizeTrackPointTs(Number(raw.ts));
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return undefined;
  return {
    lat,
    lng,
    ts,
    source: typeof raw.source === 'string' ? raw.source : undefined,
  };
}

function associationDebug(value: unknown): Marker['last_association'] {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const score = Number(raw.score);
  const threshold = Number(raw.threshold);
  if (!Number.isFinite(score) || !Number.isFinite(threshold)) return undefined;
  return {
    score,
    threshold,
    distance_km: Number(raw.distance_km) || 0,
    radius_km: Number(raw.radius_km) || 0,
    same_place: raw.same_place === true,
    same_upstream_track: raw.same_upstream_track === true,
    count_penalty: Number(raw.count_penalty) || 0,
    bearing_penalty: Number(raw.bearing_penalty) || 0,
    corridor_penalty: Number(raw.corridor_penalty) || 0,
    innovation_penalty: Number(raw.innovation_penalty) || 0,
    accepted: raw.accepted === true,
    reason: String(raw.reason || ''),
  };
}

export function mapStoreRecordToMarker(m: Record<string, unknown>): Marker {
  const rawLat = Number(m.lat);
  const rawLng = Number(m.lng);
  // Use back-projected position when the renderer determined it's more accurate
  const positionEstimated = Boolean(m.position_estimated);
  const lat = positionEstimated && Number.isFinite(Number(m.rendered_lat))
    ? Number(m.rendered_lat) : rawLat;
  const lng = positionEstimated && Number.isFinite(Number(m.rendered_lng))
    ? Number(m.rendered_lng) : rawLng;
  const lastEp = m.last_update_epoch as number | undefined;
  const createdEp = m.created_at_epoch as number | undefined;
  const flightPhase = m.flight_phase as Marker['flight_phase'] | undefined;
  const tt = (m.threat_type || m.type || 'default') as string;
  const speedCap = maxSpeedKmhForThreatType(tt);
  const sk = clampOptionalSpeed(m.speed_kmh as number | undefined, speedCap);
  const csk = clampOptionalSpeed(m.computed_speed_kmh as number | undefined, speedCap);
  const rawTraj = m.trajectory as Record<string, unknown> | undefined;

  // P5-B: Synthesize a trajectory for tracked targets that have no worker-built trajectory.
  // Use the stored EKF predicted_position as the end-point with moderate confidence.
  // Only applied when: no worker trajectory, target has a bearing, and predicted_position differs.
  let synthTraj: Record<string, unknown> | null = null;
  if (!rawTraj) {
    const predPos = m.predicted_position as { lat?: number; lng?: number } | undefined;
    const bearing = m.course_bearing as number | null | undefined;
    const posSource = m.position_source as string | undefined;
    const obsCount = m.observation_count as number | undefined;
    if (
      predPos &&
      typeof predPos.lat === 'number' &&
      typeof predPos.lng === 'number' &&
      typeof bearing === 'number' &&
      Number.isFinite(rawLat) &&
      Number.isFinite(rawLng) &&
      (posSource === 'ekf' || (typeof obsCount === 'number' && obsCount >= 2))
    ) {
      const distLat = Math.abs(predPos.lat - rawLat);
      const distLng = Math.abs(predPos.lng - rawLng);
      if (distLat > 0.005 || distLng > 0.005) {
        // P5-C: boost prediction_confidence based on how many EKF updates have been seen.
        const rawObs = typeof obsCount === 'number' ? obsCount : 1;
        const ekfConfidence = Math.min(0.85, 0.3 + rawObs * 0.05);
        synthTraj = {
          start: [rawLat, rawLng],
          end: [predPos.lat, predPos.lng],
          predicted: true,
          source: 'ekf_projection',
          prediction_confidence: ekfConfidence,
        };
      }
    }
  }

  let trajectoryOut: Marker['trajectory'] = null;
  if (rawTraj) {
    const ends = sanitizeTrajectoryEndpoints(
      rawTraj.start as [number, number] | undefined,
      rawTraj.end as [number, number] | undefined,
      tt,
    );
    const wpts = sanitizeTrajectoryWaypoints(
      rawTraj.waypoints as [number, number][] | undefined,
      tt,
    );
    trajectoryOut = {
      start: ends.start,
      end: ends.end,
      predicted: rawTraj.predicted as boolean | undefined,
      source: rawTraj.source as Trajectory['source'],
      prediction_confidence: rawTraj.prediction_confidence as number | undefined,
      waypoints: wpts,
      flight_phase: rawTraj.flight_phase as Trajectory['flight_phase'],
    };
    const hasGeom =
      trajectoryOut.start ||
      trajectoryOut.end ||
      (trajectoryOut.waypoints && trajectoryOut.waypoints.length > 0);
    const hasMeta =
      trajectoryOut.predicted != null ||
      trajectoryOut.source != null ||
      trajectoryOut.prediction_confidence != null ||
      trajectoryOut.flight_phase != null;
    if (!hasGeom && !hasMeta) trajectoryOut = null;
  } else if (synthTraj) {
    const ends = sanitizeTrajectoryEndpoints(
      synthTraj.start as [number, number],
      synthTraj.end as [number, number],
      tt,
    );
    if (ends.start || ends.end) {
      trajectoryOut = {
        start: ends.start,
        end: ends.end,
        predicted: true,
        source: 'ekf_projection' as const,
        prediction_confidence: synthTraj.prediction_confidence as number,
        // P5-E: propagate worker-supplied trajectory confidence
        trajectory_confidence: typeof m.trajectory_confidence === 'number' ? m.trajectory_confidence : undefined,
      };
    }
  }
  return {
    id: m.id as string,
    track_id: (m.track_id || undefined) as string | undefined,
    lat,
    lng,
    rendered_lat: Number.isFinite(Number(m.rendered_lat)) ? Number(m.rendered_lat) : undefined,
    rendered_lng: Number.isFinite(Number(m.rendered_lng)) ? Number(m.rendered_lng) : undefined,
    threat_type: tt,
    place: (m.place || m.city || m.location || '') as string,
    region: (m.region || '') as string,
    text: (m.text || '') as string,
    date: (m.date || m.timestamp || m.ts || '') as string,
    count: (m.count || 1) as number,
    marker_icon: (m.marker_icon || '') as string,
    course_bearing: (m.course_bearing as number) || null,
    course_direction: (m.course_direction || '') as string,
    distance_km: (m.distance_km as number) || undefined,
    speed_kmh: sk,
    computed_speed_kmh: csk,
    confidence: (m.confidence as number) || undefined,
    confidence_0_100: (m.confidence_0_100 as number) || undefined,
    placement_mode: (m.placement_mode || '') as string,
    resolve_status: (m.resolve_status || '') as string,
    trajectory: trajectoryOut,
    trajectory_source: (m.trajectory_source || '') as string,
    prediction_confidence: (m.prediction_confidence as number) || undefined,
    created_at_epoch: createdEp || undefined,
    last_update_epoch: lastEp || undefined,
    origin: (m.origin || '') as string,
    flight_phase: flightPhase,
    ticker_bearing: (m.ticker_bearing as number) ?? null,
    is_estimated: Boolean(m.is_estimated),
    track_state: m.track_state as Marker['track_state'],
    track_confidence: typeof m.track_confidence === 'number' ? m.track_confidence : undefined,
    motion_reason: typeof m.motion_reason === 'string' ? m.motion_reason : undefined,
    last_observation_epoch:
      typeof m.last_observation_epoch === 'number' ? m.last_observation_epoch : undefined,
    positions: Array.isArray(m.positions)
      ? sanitizeTrackPoints(
          (m.positions as Array<Record<string, unknown>>).slice(-24).map((p) => ({
            lat: Number(p.lat),
            lng: Number(p.lng),
            ts: normalizeTrackPointTs(Number(p.ts)),
            source: (p.source || '') as string,
          })),
          speedCap,
        ).slice(-20)
      : undefined,
    observations: Array.isArray(m.observations)
      ? sanitizeTrackPoints(
          (m.observations as Array<Record<string, unknown>>).slice(-24).map((p) => ({
            lat: Number(p.lat),
            lng: Number(p.lng),
            ts: normalizeTrackPointTs(Number(p.ts)),
            source: (p.source || '') as string,
          })),
          speedCap,
        ).slice(-20)
      : undefined,
    rejected_observations: Array.isArray(m.rejected_observations)
      ? sanitizeTrackPoints(
          (m.rejected_observations as Array<Record<string, unknown>>).slice(-24).map((p) => ({
            lat: Number(p.lat),
            lng: Number(p.lng),
            ts: normalizeTrackPointTs(Number(p.ts)),
            source: (p.source || '') as string,
            reason: (p.reason || '') as string,
            confidence: typeof p.confidence === 'number' ? p.confidence : Number(p.confidence),
          })),
          speedCap,
          { burstFactor: 99, minDistKmForSpike: Number.POSITIVE_INFINITY },
        ).slice(-20) as Marker['rejected_observations']
      : undefined,
    observation_count: (m.observation_count as number) || undefined,
    oblast: (m.oblast || '') as string,
    resolved_oblast_hasc: (m.resolved_oblast_hasc as string) || undefined,
    region_key: (m.region_key as string) || undefined,
    manual: Boolean(m.manual),
    geocode_tier: (m.geocode_tier as string) || undefined,
    geo_decision_reason: (m.geo_decision_reason as string) || undefined,
    geocode_source: (m.geocode_source as string) || undefined,
    candidates_count: typeof m.candidates_count === 'number' ? m.candidates_count : undefined,
    candidates: m.candidates as Marker['candidates'],
    event_fingerprint: typeof m.event_fingerprint === 'string' ? m.event_fingerprint : undefined,
    target_lifecycle_state: m.target_lifecycle_state as Marker['target_lifecycle_state'],
    target_confidence: typeof m.target_confidence === 'number' ? m.target_confidence : undefined,
    source_count: typeof m.source_count === 'number' ? m.source_count : undefined,
    publication_class: m.publication_class as Marker['publication_class'],
    publication_score: typeof m.publication_score === 'number' ? m.publication_score : undefined,
    publication_reasons: Array.isArray(m.publication_reasons)
      ? (m.publication_reasons as string[])
      : undefined,
    // ── Drone tracker renderer fields ────────────────────────────────────────
    is_loitering: m.is_loitering === true ? true : undefined,
    heading_confidence: (m.heading_confidence as Marker['heading_confidence']) || undefined,
    position_estimated: m.position_estimated === true ? true : undefined,
    eta_seconds: typeof m.eta_seconds === 'number' ? m.eta_seconds : undefined,
    display_confidence: typeof m.display_confidence === 'number' ? m.display_confidence : undefined,
    last_observation: pointState(m.last_observation),
    predicted_position: pointState(m.predicted_position),
    last_measurement: pointState(m.last_measurement),
    last_association: associationDebug(m.last_association),
    association_score: typeof m.association_score === 'number' ? m.association_score : undefined,
    association_reason: typeof m.association_reason === 'string' ? m.association_reason : undefined,
    // P3-A: tracker renderer trail and target destination
    tracker_trail: Array.isArray(m.tracker_trail) ? (m.tracker_trail as [number, number][]) : undefined,
    tracker_target: Array.isArray(m.tracker_target) ? (m.tracker_target as [number, number]) : (m.tracker_target === null ? null : undefined),
    position_source: typeof m.position_source === 'string' ? m.position_source : undefined,
    // tracker-plan-v3 new fields
    tqi: typeof m.tqi === 'number' ? m.tqi : undefined,
    altitude_mode: (m.altitude_mode as Marker['altitude_mode']) || undefined,
    coastal_transition: m.coastal_transition === true ? true : undefined,
    trajectory_confidence: typeof m.trajectory_confidence === 'number' ? m.trajectory_confidence : undefined,
    formation_id: typeof m.formation_id === 'string' ? m.formation_id : undefined,
    tracker_oblast_hasc: typeof m.tracker_oblast_hasc === 'string' ? m.tracker_oblast_hasc : undefined,
    // tracker-plan-v4 new fields
    burst_score: typeof m.burst_score === 'number' ? m.burst_score : undefined,
    maneuver_detected: m.maneuver_detected === true ? true : undefined,
    eta_p10: typeof m.eta_p10 === 'number' ? m.eta_p10 : undefined,
    eta_p90: typeof m.eta_p90 === 'number' ? m.eta_p90 : undefined,
    swarm_centroid: m.swarm_centroid as Marker['swarm_centroid'] | undefined,
    cross_oblast_score: typeof m.cross_oblast_score === 'number' ? m.cross_oblast_score : undefined,
    split_shallow_angle: typeof m.split_shallow_angle === 'boolean' ? m.split_shallow_angle : undefined,
    ghost_pool_origin: typeof m.ghost_pool_origin === 'string' ? m.ghost_pool_origin : undefined,
    negative_evidence_score: typeof m.negative_evidence_score === 'number' ? m.negative_evidence_score : undefined,
    origin_inference: m.origin_inference as Marker['origin_inference'] | undefined,
    trajectory_feedback: m.trajectory_feedback as Marker['trajectory_feedback'] | undefined,
    threat_type_reclassified_from: typeof m.threat_type_reclassified_from === 'string' ? m.threat_type_reclassified_from : undefined,
  } as Marker;
}

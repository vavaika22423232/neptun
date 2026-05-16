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
  }
  return {
    id: m.id as string,
    track_id: (m.track_id || undefined) as string | undefined,
    lat,
    lng,
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
  } as Marker;
}

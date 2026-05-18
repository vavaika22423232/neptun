/**
 * Pure serialization helpers for TrackedTarget — no Redis, no SSE, no server imports.
 * Used by tracked-target-store.ts and directly importable in unit tests.
 */
import { type TrackedTarget } from '@/lib/target-tracker-engine';
import { KalmanFilter2D, type KalmanFilterJSON } from '@/lib/ekf';
import type { MarkerPublicationDecision } from '@/lib/public-marker-policy';

type StoredPublication = NonNullable<TrackedTarget['publication']>;
type StoredPointState = NonNullable<TrackedTarget['last_observation']>;
type StoredAssociation = NonNullable<TrackedTarget['last_association']>;

function numberOrUndefined(value: unknown): number | undefined {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function countOrOne(value: unknown): number {
  const n = numberOrUndefined(value);
  if (n == null) return 1;
  return Math.max(1, Math.min(50, Math.round(n)));
}

function finiteNumberOr(value: unknown, fallback: number): number {
  const n = numberOrUndefined(value);
  return n == null ? fallback : n;
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim() !== '');
}

function sanitizeHistory(value: unknown): TrackedTarget['history'] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const raw = item as Record<string, unknown>;
      const lat = numberOrUndefined(raw.lat);
      const lng = numberOrUndefined(raw.lng);
      const ts = numberOrUndefined(raw.ts);
      if (lat == null || lng == null || ts == null) return null;
      const channelPriority = numberOrUndefined(raw.channel_priority);
      const count = countOrOne(raw.count);
      const msgText = typeof raw.message_text === 'string' && raw.message_text.length > 0
        ? raw.message_text
        : undefined;
      return {
        fingerprint: String(raw.fingerprint || ''),
        ts,
        lat,
        lng,
        source: String(raw.source || 'unknown'),
        ...(channelPriority !== undefined && { channel_priority: channelPriority }),
        ...(count > 1 && { count }),
        ...(msgText !== undefined && { message_text: msgText }),
        accepted: raw.accepted !== false,
        reason: String(raw.reason || ''),
        confidence: finiteNumberOr(raw.confidence, 0),
      };
    })
    .filter((item): item is TrackedTarget['history'][number] => Boolean(item));
}

function sanitizePublication(value: unknown): TrackedTarget['publication'] {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  return {
    classification: String(raw.classification || 'REJECTED') as StoredPublication['classification'],
    public: raw.public === true,
    score: finiteNumberOr(raw.score, 0),
    scores: raw.scores && typeof raw.scores === 'object'
      ? raw.scores as StoredPublication['scores']
      : { extraction: 0, locality: 0, source: 0, motion: 0, evidence: 0, publication: 0 },
    fingerprint: String(raw.fingerprint || ''),
    reasons: stringArray(raw.reasons),
    invariantViolations: stringArray(raw.invariantViolations),
  };
}

function sanitizePointState(value: unknown): StoredPointState | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const lat = numberOrUndefined(raw.lat);
  const lng = numberOrUndefined(raw.lng);
  const ts = numberOrUndefined(raw.ts);
  if (lat == null || lng == null || ts == null) return undefined;
  return {
    lat,
    lng,
    ts,
    source: typeof raw.source === 'string' ? raw.source : undefined,
    confidence: numberOrUndefined(raw.confidence),
    reason: typeof raw.reason === 'string' ? raw.reason : undefined,
  };
}

function sanitizeAssociation(value: unknown): StoredAssociation | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const score = numberOrUndefined(raw.score);
  const threshold = numberOrUndefined(raw.threshold);
  if (score == null || threshold == null) return undefined;
  return {
    score,
    threshold,
    distance_km: finiteNumberOr(raw.distance_km, 0),
    radius_km: finiteNumberOr(raw.radius_km, 0),
    same_place: raw.same_place === true,
    same_upstream_track: raw.same_upstream_track === true,
    count_penalty: finiteNumberOr(raw.count_penalty, 0),
    bearing_penalty: finiteNumberOr(raw.bearing_penalty, 0),
    corridor_penalty: finiteNumberOr(raw.corridor_penalty, 0),
    innovation_penalty: finiteNumberOr(raw.innovation_penalty, 0),
    accepted: raw.accepted === true,
    reason: String(raw.reason || ''),
  };
}

/** Reconstruct a KalmanFilter2D from its serialized JSON form. Returns undefined on invalid data. */
function deserializeEkf(value: unknown): KalmanFilter2D | undefined {
  if (!value || typeof value !== 'object') return undefined;
  try {
    const ekfRaw = value as KalmanFilterJSON;
    if (
      !Array.isArray(ekfRaw.state) ||
      ekfRaw.state.length !== 4 ||
      !Array.isArray(ekfRaw.P) ||
      typeof ekfRaw.qProcessNoise !== 'number' ||
      typeof ekfRaw.rMeasurementNoise !== 'number'
    ) return undefined;
    return KalmanFilter2D.fromJSON(ekfRaw);
  } catch {
    return undefined;
  }
}

/**
 * Validate and coerce an arbitrary plain object (e.g. from Redis JSON.parse) into a
 * well-typed TrackedTarget, reconstructing KalmanFilter2D from serialized state.
 * Returns null if the object is too malformed to use.
 */
export function sanitizeTrackedTarget(value: unknown): TrackedTarget | null {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Record<string, unknown>;
  const id = typeof raw.id === 'string' && raw.id.trim() ? raw.id : null;
  const lat = numberOrUndefined(raw.lat);
  const lng = numberOrUndefined(raw.lng);
  if (!id || lat == null || lng == null) return null;
  const movement = raw.movement_vector && typeof raw.movement_vector === 'object'
    ? raw.movement_vector as Record<string, unknown>
    : {};
  const history = sanitizeHistory(raw.history);
  const fingerprints = stringArray(raw.event_fingerprints);
  const lastSeen = finiteNumberOr(raw.last_seen, history[history.length - 1]?.ts ?? Date.now());
  const upstreamTrackIds = stringArray(raw.upstream_track_ids);

  return {
    id,
    threat_type: String(raw.threat_type || raw.type || 'unknown'),
    region: typeof raw.region === 'string' ? raw.region : undefined,
    place: typeof raw.place === 'string' ? raw.place : undefined,
    lat,
    lng,
    count: countOrOne(raw.count),
    confidence: finiteNumberOr(raw.confidence, 0),
    reliability: finiteNumberOr(raw.reliability, 0),
    source_count: Math.max(0, Math.round(finiteNumberOr(raw.source_count, stringArray(raw.sources).length))),
    sources: stringArray(raw.sources),
    upstream_track_ids: upstreamTrackIds,
    lifecycle_state: String(raw.lifecycle_state || 'DETECTED') as TrackedTarget['lifecycle_state'],
    first_seen: finiteNumberOr(raw.first_seen, history[0]?.ts ?? lastSeen),
    last_seen: lastSeen,
    movement_vector: {
      bearing_deg: numberOrUndefined(movement.bearing_deg) ?? null,
      speed_kmh: numberOrUndefined(movement.speed_kmh) ?? null,
    },
    speed_estimate_kmh: numberOrUndefined(raw.speed_estimate_kmh) ?? null,
    history,
    event_fingerprints: fingerprints,
    publication: sanitizePublication(raw.publication),
    manual: raw.manual === true,
    last_observation: sanitizePointState(raw.last_observation),
    predicted_position: sanitizePointState(raw.predicted_position),
    last_measurement: sanitizePointState(raw.last_measurement),
    last_association: sanitizeAssociation(raw.last_association),
    is_loitering: raw.is_loitering === true ? true : undefined,
    heading_confidence: typeof raw.heading_confidence === 'string'
      ? raw.heading_confidence as TrackedTarget['heading_confidence']
      : undefined,
    position_estimated: raw.position_estimated === true ? true : undefined,
    eta_seconds: numberOrUndefined(raw.eta_seconds) ?? null,
    display_confidence: numberOrUndefined(raw.display_confidence),
    rendered_lat: numberOrUndefined(raw.rendered_lat),
    rendered_lng: numberOrUndefined(raw.rendered_lng),
    last_message_text: typeof raw.last_message_text === 'string' ? raw.last_message_text : undefined,
    last_resolve_status: typeof raw.last_resolve_status === 'string' ? raw.last_resolve_status : undefined,
    last_placement_mode: typeof raw.last_placement_mode === 'string' ? raw.last_placement_mode : undefined,
    parent_track_id: typeof raw.parent_track_id === 'string' ? raw.parent_track_id : undefined,
    swarm_cluster_id: typeof raw.swarm_cluster_id === 'string' ? raw.swarm_cluster_id : undefined,
    ekf: deserializeEkf(raw.ekf),
    // P3-A: restore renderer trail/target from Redis
    tracker_trail: Array.isArray(raw.tracker_trail)
      ? (raw.tracker_trail as [number, number][]).filter(
          (p) => Array.isArray(p) && typeof p[0] === 'number' && typeof p[1] === 'number',
        )
      : undefined,
    tracker_target: Array.isArray(raw.tracker_target)
      ? (raw.tracker_target as [number, number])
      : raw.tracker_target === null
        ? null
        : undefined,
    // tracker-plan-v3 new fields
    tqi: numberOrUndefined(raw.tqi),
    altitude_mode: typeof raw.altitude_mode === 'string'
      ? raw.altitude_mode as TrackedTarget['altitude_mode']
      : undefined,
    coastal_transition: raw.coastal_transition === true ? true : undefined,
    trajectory_confidence: numberOrUndefined(raw.trajectory_confidence),
    formation_id: typeof raw.formation_id === 'string' ? raw.formation_id : undefined,
    publication_history: Array.isArray(raw.publication_history)
      ? (raw.publication_history as TrackedTarget['publication_history'])
      : undefined,
  };
}

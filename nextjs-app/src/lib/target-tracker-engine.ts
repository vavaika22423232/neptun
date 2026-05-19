import {
  computeMarkerEventFingerprint,
  evaluateMarkerPublication,
  type MarkerPublicationDecision,
} from '@/lib/public-marker-policy';
import type { AdminSettings } from '@/lib/admin/data';
import { destinationPoint, haversineKm, normalizeEpochMs } from '@/lib/marker-movement-policy';
import { trackMotionProfile, getWindVector } from '@/lib/track-motion-profile';
import {
  buildTrackerRenderDescriptor,
  type TrackerEvent as RendererEvent,
} from '@/lib/drone-tracker-renderer';
import { KalmanFilter2D, IMMFilter2D, type IMMFilterJSON } from '@/lib/ekf';

export type TargetLifecycleState =
  | 'DETECTED'
  | 'TRACKING'
  | 'CONFIRMED'
  | 'LOST'
  | 'STALE'
  | 'DESTROYED'
  | 'REJECTED';

export type CandidateEvent = {
  event_id?: string;
  fingerprint?: string;
  upstream_track_id?: string;
  ts: number;
  lat: number;
  lng: number;
  threat_type: string;
  count?: number;
  region?: string;
  place?: string;
  source?: string;
  channel_priority?: number;
  confidence?: number;
  locality_confidence?: number;
  bearing_deg?: number | null;
  sensor_type?: 'acoustic' | 'radar' | 'visual';
  raw?: Record<string, unknown>;
  manual?: boolean;
};

export type TargetHistoryItem = {
  fingerprint: string;
  ts: number;
  lat: number;
  lng: number;
  source: string;
  channel_priority?: number;
  count?: number;
  accepted: boolean;
  reason: string;
  confidence: number;
  /** Raw message text, stored for cross-channel repost deduplication (P3-D). */
  message_text?: string;
};

export type TargetPointState = {
  lat: number;
  lng: number;
  ts: number;
  source?: string;
  confidence?: number;
  reason?: string;
};

export type TargetAssociationBreakdown = {
  score: number;
  threshold: number;
  distance_km: number;
  radius_km: number;
  same_place: boolean;
  same_upstream_track: boolean;
  count_penalty: number;
  bearing_penalty: number;
  corridor_penalty: number;
  innovation_penalty: number;
  quality_penalty?: number;
  group_bonus?: number;
  text_intent?: string;
  observation_quality?: string;
  accepted: boolean;
  reason: string;
};

export type TrackedTarget = {
  id: string;
  threat_type: string;
  region?: string;
  place?: string;
  lat: number;
  lng: number;
  count: number;
  confidence: number;
  reliability: number;
  source_count: number;
  sources: string[];
  upstream_track_ids: string[];
  lifecycle_state: TargetLifecycleState;
  first_seen: number;
  last_seen: number;
  movement_vector: { bearing_deg: number | null; speed_kmh: number | null };
  speed_estimate_kmh: number | null;
  air_speed_kmh?: number | null;
  history: TargetHistoryItem[];
  event_fingerprints: string[];
  publication?: MarkerPublicationDecision;
  manual?: boolean;
  ekf?: KalmanFilter2D | IMMFilter2D;
  parent_track_id?: string;
  swarm_cluster_id?: string;
  last_observation?: TargetPointState;
  predicted_position?: TargetPointState;
  last_measurement?: TargetPointState;
  last_association?: TargetAssociationBreakdown;
  // ── Renderer output (applied after every create/update) ──────────────────
  is_loitering?: boolean;
  heading_confidence?: 'explicit' | 'track' | 'regional' | 'unknown';
  position_estimated?: boolean;
  eta_seconds?: number | null;
  display_confidence?: number;
  /** The rendered position may differ from raw lat/lng when back-projected */
  rendered_lat?: number;
  rendered_lng?: number;
  /** Renderer-computed trail [[lat,lng],…] oldest→newest for polyline display (P3-A) */
  tracker_trail?: [number, number][];
  /** Renderer-computed target destination [lat,lng] if known (P3-A) */
  tracker_target?: [number, number] | null;
  last_message_text?: string;
  last_resolve_status?: string;
  last_placement_mode?: string;
  /** Last accepted coordinate quality used by association/rendering. */
  last_observation_quality?: 'observed' | 'estimated' | 'coarse' | 'target_hint';
  /** Text intent inferred from the latest marker message. */
  last_text_intent?: 'single' | 'group' | 'additional' | 'loss' | 'unknown';
  /** Composite track quality index 0–100 (P4-A). */
  tqi?: number;
  /** Altitude mode inferred from message text (P3-E). */
  altitude_mode?: 'low_altitude' | 'ballistic_arc' | 'unknown';
  /** Whether this track is transitioning from sea to land (P3-B). */
  coastal_transition?: boolean;
  /** Worker-supplied trajectory confidence 0..1 (P5-E). */
  trajectory_confidence?: number;
  /** Formation group id when part of a detected tactical formation (P3-C). */
  formation_id?: string;
  /** Recent publication decisions for audit/admin display (P4-D). */
  publication_history?: Array<{ ts: number; public: boolean; classification: string; reason: string }>;
  /** P1-C: Score 0..1 indicating burst (many co-temporal events) vs lone event. */
  burst_score?: number;
  /** P1-E: Previous threat types observed, for morphing detection. */
  threat_type_history?: string[];
  /** P2-A: IMM filter JSON for serialization. If present, imm_filter is the active IMM. */
  imm?: IMMFilterJSON;
  /** P2-B: True when the jerk signal indicates an active maneuver. */
  maneuver_detected?: boolean;
  /** P2-C: 10th/90th percentile ETA from Monte Carlo simulation (seconds). */
  eta_p10?: number | null;
  eta_p90?: number | null;
  /** P3-A: Swarm flock centroid when this target belongs to a cluster with a computed centroid. */
  swarm_centroid?: { lat: number; lng: number; size: number };
  /** P3-B: Cross-oblast correlation score — higher = part of a multi-oblast wave. */
  cross_oblast_score?: number;
  /** P3-C: Split angle — true when split angle < 45° (shallow, likely separation, not turn). */
  split_shallow_angle?: boolean;
  /** P3-D: True when the event was gated out by time-of-flight check (missile range gate). */
  tof_gate_failed?: boolean;
  /** P3-E: ID of the ghost-pool entry that handed off to this track. */
  ghost_pool_origin?: string;
  /** P4-B: Timestamp when the stale reaper last attempted to expire this track. */
  reaper_checked_at?: number;
  /** P5-B: Negative evidence score — higher = more all-clear suppression signals. */
  negative_evidence_score?: number;
  /** P5-C: Inferred launch origin from backward projection. */
  origin_inference?: { lat: number; lng: number; confidence: number; method: string };
  /** P5-D: Trajectory accuracy feedback from worker — diff between predicted and actual landing. */
  trajectory_feedback?: { error_km: number; reported_at: number };
  /** P5-E: Most recent reclassification event if threat type was changed dynamically. */
  threat_type_reclassified_from?: string;
  /** P6-F: Multi-Hypothesis Tracking (MHT) branch relationships */
  mht_parent_id?: string;
  mht_branch_score?: number;
};

export type TrackerDecision =
  | {
      action: 'REPLAY_SUPPRESSED';
      target: TrackedTarget;
      reason: string;
      fingerprint: string;
    }
  | {
      action: 'TARGET_UPDATED' | 'TARGET_CREATED' | 'EVENT_REJECTED' | 'EVENT_QUARANTINED';
      target: TrackedTarget | null;
      reason: string;
      fingerprint: string;
      publication?: MarkerPublicationDecision;
    };

export type TrackerOptions = {
  associationRadiusKm?: number;
  replayWindowMs?: number;
  maxHistory?: number;
  initialTargets?: TrackedTarget[];
};

const DEFAULT_REPLAY_WINDOW_MS = 6 * 60 * 60_000;
const DEFAULT_MAX_HISTORY = 40;
const ASSOCIATION_SCORE_MIN = 48;

function clamp(v: number, min: number, max: number): number {
  if (!Number.isFinite(v)) return min;
  return Math.max(min, Math.min(max, v));
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

function norm(value: unknown): string {
  return String(value || '').normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ');
}

function normalizeCount(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return 1;
  return Math.max(1, Math.min(50, Math.round(n)));
}

function normalizeTrackId(value: unknown): string {
  return String(value || '').normalize('NFKC').trim();
}

function bearingBetween(aLat: number, aLng: number, bLat: number, bLng: number): number | null {
  const dLat = bLat - aLat;
  const midLat = (aLat + bLat) / 2;
  const dLng = (bLng - aLng) * Math.cos((midLat * Math.PI) / 180);
  if (Math.abs(dLat) <= 0.0001 && Math.abs(dLng) <= 0.0001) return null;
  return (Math.atan2(dLng, dLat) * 180 / Math.PI + 360) % 360;
}

function segmentDistanceKm(
  aLat: number,
  aLng: number,
  bLat: number,
  bLng: number,
  pLat: number,
  pLng: number,
): number {
  const meanLat = ((aLat + bLat + pLat) / 3) * Math.PI / 180;
  const kmPerDegLat = 111.32;
  const kmPerDegLng = 111.32 * Math.cos(meanLat);
  const ax = aLng * kmPerDegLng;
  const ay = aLat * kmPerDegLat;
  const bx = bLng * kmPerDegLng;
  const by = bLat * kmPerDegLat;
  const px = pLng * kmPerDegLng;
  const py = pLat * kmPerDegLat;
  const vx = bx - ax;
  const vy = by - ay;
  const wx = px - ax;
  const wy = py - ay;
  const len2 = vx * vx + vy * vy;
  if (len2 <= 0.000001) return haversineKm(aLat, aLng, pLat, pLng);
  const t = clamp((wx * vx + wy * vy) / len2, 0, 1);
  const cx = ax + vx * t;
  const cy = ay + vy * t;
  return Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
}

/**
 * P1-E: Fast bbox-based oblast HASC resolver for tracker geo-context enrichment.
 * Covers Ukraine's 25 oblasts + Kyiv city with approximate bounding boxes.
 */
function resolveOblastHasc(lat: number, lng: number): string | null {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  // [minLat, maxLat, minLng, maxLng, hasc]
  const BBOX: [number, number, number, number, string][] = [
    [50.21, 51.97, 30.24, 31.98, 'UA.KV'],  // Kyiv region
    [50.35, 50.62, 30.37, 30.86, 'UA.KC'],  // Kyiv city
    [49.55, 52.38, 33.45, 35.55, 'UA.KK'],  // Kharkiv
    [48.23, 50.40, 32.97, 36.10, 'UA.DN'],  // Dnipropetrovsk
    [47.74, 48.58, 35.86, 38.37, 'UA.DT'],  // Donetsk (partial)
    [47.78, 49.08, 37.53, 39.99, 'UA.LH'],  // Luhansk (partial)
    [46.88, 48.48, 32.42, 35.10, 'UA.ZP'],  // Zaporizhzhia
    [46.20, 47.57, 31.10, 35.60, 'UA.KS'],  // Kherson
    [46.25, 47.83, 29.60, 32.60, 'UA.MY'],  // Mykolaiv
    [45.93, 47.56, 29.80, 31.60, 'UA.OD'],  // Odesa
    [48.01, 49.72, 28.83, 32.00, 'UA.VN'],  // Vinnytsia
    [50.23, 51.78, 27.68, 30.55, 'UA.ZT'],  // Zhytomyr
    [50.60, 52.38, 30.85, 35.52, 'UA.CK'],  // Chernihiv
    [51.07, 52.37, 31.55, 35.30, 'UA.SM'],  // Sumy
    [49.21, 51.06, 26.48, 29.67, 'UA.KM'],  // Khmelnytskyi
    [49.25, 50.40, 24.50, 28.95, 'UA.TN'],  // Ternopil
    [49.79, 51.27, 21.88, 25.32, 'UA.LV'],  // Lviv
    [48.18, 50.37, 23.26, 27.19, 'UA.IF'],  // Ivano-Frankivsk
    [47.73, 49.60, 22.47, 25.34, 'UA.ZK'],  // Zakarpattia
    [47.83, 48.80, 27.73, 30.50, 'UA.OD'],  // (extended Odesa N)
    [49.03, 50.62, 31.57, 34.00, 'UA.PL'],  // Poltava
    [49.51, 50.93, 28.93, 32.31, 'UA.CK'],  // Cherkasy
    [47.89, 49.53, 30.68, 34.50, 'UA.KR'],  // Kirovohrad
    [49.50, 51.55, 25.27, 28.99, 'UA.RV'],  // Rivne
    [51.27, 52.38, 23.40, 27.80, 'UA.VO'],  // Volyn
    [48.55, 51.06, 24.03, 28.12, 'UA.LN'],  // Lviv (north ext)
    [51.20, 52.38, 29.49, 32.18, 'UA.CН'],  // Chernihiv (south)
    [48.47, 49.93, 33.51, 36.27, 'UA.PL'],  // Poltava (east ext)
  ];
  for (const [minLat, maxLat, minLng, maxLng, hasc] of BBOX) {
    if (lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng) return hasc;
  }
  return null;
}

/**
 * P3-D: Jaccard similarity of 3-char shingles for cross-channel repost deduplication.
 * Returns 0..1. Values ≥ 0.72 indicate likely copy-paste reposts across channels.
 */
function textShinglingSimilarity(a: string, b: string): number {
  if (!a || !b) return 0;
  const shingle = (s: string): Set<string> => {
    const out = new Set<string>();
    const clean = s.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
    for (let i = 0; i <= clean.length - 3; i++) out.add(clean.slice(i, i + 3));
    return out;
  };
  const sa = shingle(a);
  const sb = shingle(b);
  if (sa.size === 0 && sb.size === 0) return 1;
  if (sa.size === 0 || sb.size === 0) return 0;
  let inter = 0;
  for (const t of sa) { if (sb.has(t)) inter++; }
  return inter / (sa.size + sb.size - inter);
}

function angularDiffDeg(a: number, b: number): number {
  const diff = Math.abs(a - b) % 360;
  return Math.min(diff, 360 - diff);
}

function blendBearingDeg(previous: number | null, observed: number | null, alpha: number): number | null {
  if (observed == null || !Number.isFinite(observed)) return previous;
  if (previous == null || !Number.isFinite(previous)) return observed;
  const prevRad = previous * Math.PI / 180;
  const obsRad = observed * Math.PI / 180;
  const x = Math.cos(prevRad) * (1 - alpha) + Math.cos(obsRad) * alpha;
  const y = Math.sin(prevRad) * (1 - alpha) + Math.sin(obsRad) * alpha;
  if (Math.abs(x) < 0.000001 && Math.abs(y) < 0.000001) return observed;
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

function stableTargetId(event: CandidateEvent): string {
  // P4-A: Robust hash — include threat_type, quantized bearing bucket, and full place hash.
  // Bearing quantised to 45° buckets so two targets in same place moving in opposite
  // directions (e.g. split swarm legs) get different stable IDs.
  const bearingBucket = event.bearing_deg != null
    ? Math.round(event.bearing_deg / 45) % 8
    : -1;
  const seed = [
    normalizeTrackId(event.upstream_track_id),
    norm(event.threat_type),
    norm(event.region),
    norm(event.place),          // full place, not slice
    normalizeCount(event.count),
    Math.round(event.lat * 10) / 10,
    Math.round(event.lng * 10) / 10,
    bearingBucket,
  ].join('|');
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return `target_${(h >>> 0).toString(36)}`;
}

function targetIdForNewEvent(
  event: CandidateEvent,
  fingerprint: string,
  targets: Map<string, TrackedTarget>,
): string {
  const baseId = stableTargetId(event);
  if (!targets.has(baseId)) return baseId;

  let suffix = fingerprint.replace(/[^a-zA-Z0-9]/g, '').slice(0, 10);
  if (!suffix) suffix = String(Math.abs(Math.round(event.ts))).slice(-10);

  let id = `${baseId}_${suffix}`;
  let n = 2;
  while (targets.has(id)) {
    id = `${baseId}_${suffix}_${n}`;
    n += 1;
  }
  return id;
}

function eventFingerprint(event: CandidateEvent): string {
  if (event.fingerprint) return event.fingerprint;
  return computeMarkerEventFingerprint({
    channel_name: event.source,
    msg_id: event.event_id,
    text: event.raw?.text,
    threat_type: event.threat_type,
    place: event.place,
    region: event.region,
    created_at_epoch: event.ts,
  });
}

function eventToPolicyMarker(event: CandidateEvent): Record<string, unknown> {
  return {
    ...(event.raw || {}),
    lat: event.lat,
    lng: event.lng,
    threat_type: event.threat_type,
    count: normalizeCount(event.count),
    place: event.place,
    region: event.region,
    confidence: event.confidence,
    channel_name: event.source,
    channel_priority: event.channel_priority,
    created_at_epoch: event.ts,
    event_fingerprint: eventFingerprint(event),
  };
}

function sourceReliability(event: CandidateEvent): number {
  const p = Number(event.channel_priority);
  if (Number.isFinite(p) && p <= 1) return 0.95;
  if (Number.isFinite(p) && p <= 3) return 0.85;
  return 0.75;
}

function candidateConfidence(event: CandidateEvent): number {
  return Math.min(
    clamp01(event.confidence ?? 0.5),
    clamp01(event.locality_confidence ?? 0.75),
    sourceReliability(event),
  );
}

function lifecycleFor(target: TrackedTarget, publication?: MarkerPublicationDecision): TargetLifecycleState {
  if (target.lifecycle_state === 'DESTROYED' || target.lifecycle_state === 'LOST' || target.lifecycle_state === 'REJECTED') {
    return target.lifecycle_state;
  }
  if (publication?.public && (target.source_count >= 2 || target.reliability >= 0.9 || target.confidence >= 0.9)) {
    return 'CONFIRMED';
  }
  if (target.confidence >= 0.95 && target.source_count >= 2) return 'CONFIRMED';
  if (target.confidence >= 0.7) return 'TRACKING';
  if (target.confidence >= 0.4) return 'DETECTED';
  return 'REJECTED';
}

function lifecycleAt(target: TrackedTarget, nowMs: number): TargetLifecycleState {
  if (target.manual) return target.lifecycle_state;
  if (target.lifecycle_state === 'DESTROYED' || target.lifecycle_state === 'LOST' || target.lifecycle_state === 'REJECTED') {
    return target.lifecycle_state;
  }
  const profile = trackMotionProfile(target.threat_type);
  const ageMs = Math.max(0, normalizeEpochMs(nowMs, Date.now()) - normalizeEpochMs(target.last_seen, Date.now()));
  if (ageMs > profile.lostMs) return 'LOST';
  if (ageMs > profile.staleMs) return 'STALE';
  return lifecycleFor(target, target.publication);
}

function maxAssociationRadius(event: CandidateEvent, options?: TrackerOptions, target?: TrackedTarget): number {
  if (typeof options?.associationRadiusKm === 'number') return options.associationRadiusKm;
  const profile = trackMotionProfile(event.threat_type);
  const base = Math.min(70, Math.max(18, profile.nominalSpeedKmh * 0.12));
  const quality = observationQuality(event);
  const intent = inferTextIntent(event);
  const qualityBoost =
    quality === 'target_hint' ? 1.8 :
    quality === 'estimated' ? 1.35 :
    quality === 'coarse' ? 1.15 :
    1;
  const groupBoost = intent === 'group' ? 1.1 : 1;
  // Young targets haven't moved far yet — reduce radius to prevent false merges
  if (target) {
    const ageMs = Math.max(0, event.ts - target.first_seen);
    if (ageMs < 5 * 60_000) return base * 0.6 * qualityBoost * groupBoost;   // < 5 min: 60% radius
    if (ageMs < 12 * 60_000) return base * 0.8 * qualityBoost * groupBoost;  // < 12 min: 80% radius
  }
  return base * qualityBoost * groupBoost;
}

function impossibleMovement(target: TrackedTarget, event: CandidateEvent): { impossible: boolean; speedKmh: number; distKm: number } {
  const distKm = haversineKm(target.lat, target.lng, event.lat, event.lng);
  const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 1 / 3600);
  const speedKmh = distKm / dtHours;
  const profile = trackMotionProfile(event.threat_type);
  // P4-C: dt-aware threshold — implied speed must exceed maxSpeed * 1.2, not a fixed 4 km floor.
  // The old `distKm > 4` floor incorrectly allowed large gaps to slip through for slow threats.
  const minDist = Math.max(1.5, profile.nominalSpeedKmh * dtHours * 0.05); // at least 5% of nominal motion budget
  return {
    impossible: event.ts > target.last_seen && distKm > minDist && speedKmh > profile.maxSpeedKmh * 1.2,
    speedKmh,
    distKm,
  };
}

function hasSameUpstreamTrack(target: TrackedTarget, event: CandidateEvent): boolean {
  const trackId = normalizeTrackId(event.upstream_track_id);
  return !!trackId && target.upstream_track_ids.includes(trackId);
}

function hasDifferentExplicitGroup(target: TrackedTarget, event: CandidateEvent): boolean {
  const trackId = normalizeTrackId(event.upstream_track_id);
  if (!trackId || target.upstream_track_ids.length === 0 || target.upstream_track_ids.includes(trackId)) {
    return false;
  }
  return target.count > 1 || normalizeCount(event.count) > 1;
}

function projectedTargetPosition(target: TrackedTarget, atTs: number): { lat: number; lng: number; projected: boolean } {
  const bearing = target.movement_vector.bearing_deg;
  const speed = target.speed_estimate_kmh ?? target.movement_vector.speed_kmh;
  if (
    bearing == null ||
    speed == null ||
    !Number.isFinite(bearing) ||
    !Number.isFinite(speed) ||
    speed <= 0 ||
    target.is_loitering ||
    atTs <= target.last_seen
  ) {
    return { lat: target.lat, lng: target.lng, projected: false };
  }

  const profile = trackMotionProfile(target.threat_type);
  const extrapolationLimit = target.ekf ? profile.staleMs : profile.extrapolateMs;
  const elapsedMs = Math.min(Math.max(0, atTs - target.last_seen), extrapolationLimit);
  if (elapsedMs < 30_000) return { lat: target.lat, lng: target.lng, projected: false };

  // Use EKF state if available — non-mutating predictedPosition()
  if (target.ekf) {
    const elapsedSeconds = elapsedMs / 1000;
    const ekfSpeedKmh = target.ekf.speedKmh();
    const coastingSpeedFloor = elapsedMs >= 5 * 60_000 ? profile.nominalSpeedKmh * 0.75 : 0;
    if (ekfSpeedKmh < coastingSpeedFloor) {
      const projectedKm = coastingSpeedFloor * elapsedMs / 3_600_000;
      const [projLat, projLng] = destinationPoint(target.lat, target.lng, bearing, projectedKm);
      return { lat: projLat, lng: projLng, projected: true };
    }
    const pos = target.ekf.predictedPosition(elapsedSeconds);
    return { lat: pos.lat, lng: pos.lng, projected: true };
  }

  const coastingSpeedFloor = elapsedMs >= 5 * 60_000 ? profile.nominalSpeedKmh * 0.75 : 0;
  const projectedKm = Math.min(Math.max(speed, coastingSpeedFloor), profile.maxSpeedKmh) * elapsedMs / 3_600_000;
  if (projectedKm < 1) return { lat: target.lat, lng: target.lng, projected: false };

  const [lat, lng] = destinationPoint(target.lat, target.lng, bearing, projectedKm);
  return { lat, lng, projected: true };
}

function movementInnovationPenalty(target: TrackedTarget, event: CandidateEvent, distKm: number): number {
  if (event.ts <= target.last_seen) return 0;
  const profile = trackMotionProfile(event.threat_type);
  const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 1 / 3600);
  const expectedSpeed = target.speed_estimate_kmh ?? profile.nominalSpeedKmh;
  const expectedKm = Math.max(2.5, expectedSpeed * dtHours);
  const plausibleKm = Math.max(5, expectedKm * 1.85);
  if (distKm <= plausibleKm) return 0;
  return Math.min(32, (distKm / plausibleKm - 1) * 22);
}

function associationScoreThreshold(target: TrackedTarget, event: CandidateEvent, samePlace: boolean): number {
  if (hasSameUpstreamTrack(target, event)) return 26;
  if (samePlace) return 38;
  if (observationQuality(event) === 'target_hint' && target.region && event.region && norm(target.region) === norm(event.region)) {
    return 30;
  }
  return ASSOCIATION_SCORE_MIN;
}

function measurementBlendAlpha(target: TrackedTarget, event: CandidateEvent, confidence: number, rawDistKm: number): number {
  if (hasSameUpstreamTrack(target, event)) return 0.9;
  if (rawDistKm <= 0.35) return 1;

  const source = norm(event.source) || 'unknown';
  const sameSource = target.sources.includes(source);
  const samePlace = target.place && event.place && norm(target.place) === norm(event.place);
  const sourceBoost = sameSource ? -0.08 : 0.04;
  const confidenceBoost = clamp01(confidence) * 0.14;
  const placeBoost = samePlace ? 0.08 : 0;
  const jumpPenalty = rawDistKm > 8 ? 0.1 : rawDistKm > 5 ? 0.05 : 0;

  return clamp(0.58 + confidenceBoost + sourceBoost + placeBoost - jumpPenalty, 0.45, 0.88);
}

function blendCoordinate(from: number, to: number, alpha: number): number {
  return from + (to - from) * alpha;
}

function eventResolveStatus(event: CandidateEvent): string {
  return norm(event.raw?.resolve_status);
}

function eventPlacementMode(event: CandidateEvent): string {
  return norm(event.raw?.placement_mode);
}

export type ObservationQuality = 'observed' | 'estimated' | 'coarse' | 'target_hint';
export type TextIntent = 'single' | 'group' | 'additional' | 'loss' | 'unknown';

export type CandidateObservationClassification = {
  observation_quality: ObservationQuality;
  text_intent: TextIntent;
  coordinate_role: 'observation' | 'target' | 'area_centroid' | 'estimated_path';
  public_position_policy: 'precise_pin' | 'hold_existing' | 'zone_only' | 'suppress_or_admin_only';
  reasons: string[];
};

function eventText(event: CandidateEvent): string {
  return typeof event.raw?.text === 'string' ? event.raw.text : '';
}

function inferTextIntent(event: CandidateEvent): TextIntent {
  const text = eventText(event).toLowerCase();
  if (!text) {
    return normalizeCount(event.count) > 1 ? 'group' : 'unknown';
  }
  if (/без\s+(подальшої\s+)?фіксац|не\s+фіксу|втрачен[ао]\s+фіксац|зникл[аио]?|не\s+спостеріга/i.test(text)) {
    return 'loss';
  }
  if (/ще\s+один|ще\s+одна|нов(ий|а)\s+(бпла|шахед|ціль)|додатков(ий|а)|плюс\s+\d/i.test(text)) {
    return 'additional';
  }
  if (
    normalizeCount(event.count) > 1 ||
    /\b(група|групою|декілька|кілька|купа|кучу|масово|рой|роєм|пачка|хвиля)\b/i.test(text)
  ) {
    return 'group';
  }
  return 'single';
}

function observationQuality(event: CandidateEvent): ObservationQuality {
  const resolveStatus = eventResolveStatus(event);
  const placementMode = eventPlacementMode(event);
  if (
    placementMode === 'target_only_no_current_position' ||
    resolveStatus === 'trajectory_approach' ||
    resolveStatus === 'predictive_approach'
  ) {
    return 'target_hint';
  }
  if (
    resolveStatus === 'direction_geocode_fallback' ||
    resolveStatus === 'oblast_direction_only' ||
    resolveStatus === 'regional_oblast_direction_target' ||
    resolveStatus === 'estimated_trajectory' ||
    resolveStatus === 'estimated_fallback_target'
  ) {
    return 'estimated';
  }
  if (
    placementMode === 'area' ||
    placementMode === 'region' ||
    placementMode === 'fraction' ||
    resolveStatus === 'area_center' ||
    resolveStatus === 'regional_oblast_centroid' ||
    resolveStatus === 'oblast_fallback' ||
    resolveStatus === 'maritime_approach'
  ) {
    return 'coarse';
  }
  return 'observed';
}

export function classifyCandidateObservation(event: CandidateEvent): CandidateObservationClassification {
  const quality = observationQuality(event);
  const intent = inferTextIntent(event);
  const resolveStatus = eventResolveStatus(event);
  const placementMode = eventPlacementMode(event);
  const reasons: string[] = [];

  if (placementMode) reasons.push(`placement:${placementMode}`);
  if (resolveStatus) reasons.push(`resolve:${resolveStatus}`);
  if (intent !== 'unknown') reasons.push(`intent:${intent}`);
  if (normalizeCount(event.count) > 1) reasons.push(`count:${normalizeCount(event.count)}`);

  let coordinateRole: CandidateObservationClassification['coordinate_role'] = 'observation';
  if (quality === 'target_hint') coordinateRole = 'target';
  else if (quality === 'coarse') coordinateRole = 'area_centroid';
  else if (quality === 'estimated') coordinateRole = 'estimated_path';

  let publicPositionPolicy: CandidateObservationClassification['public_position_policy'] = 'precise_pin';
  if (intent === 'loss') publicPositionPolicy = 'suppress_or_admin_only';
  else if (quality === 'target_hint') publicPositionPolicy = 'hold_existing';
  else if (quality === 'coarse' || quality === 'estimated') publicPositionPolicy = 'zone_only';

  return {
    observation_quality: quality,
    text_intent: intent,
    coordinate_role: coordinateRole,
    public_position_policy: publicPositionPolicy,
    reasons,
  };
}

function qualityAssociationPenalty(quality: ObservationQuality, sameUpstreamTrack: boolean, samePlace: boolean): number {
  if (sameUpstreamTrack) return 0;
  if (quality === 'target_hint') return samePlace ? 3 : 16;
  if (quality === 'estimated') return samePlace ? 2 : 10;
  if (quality === 'coarse') return samePlace ? 1 : 7;
  return 0;
}

function groupAssociationBonus(intent: TextIntent, target: TrackedTarget, event: CandidateEvent): number {
  if (intent !== 'group') return 0;
  const eventCount = normalizeCount(event.count);
  const targetGroupish = target.count > 1 || eventCount > 1 || target.last_text_intent === 'group';
  if (!targetGroupish) return 0;
  return Math.min(10, 4 + Math.max(target.count, eventCount) * 1.0);
}

function shouldHoldWeakMeasurement(
  target: TrackedTarget,
  event: CandidateEvent,
  confidence: number,
  rawDistKm: number,
): boolean {
  if (hasSameUpstreamTrack(target, event)) return false;
  if (rawDistKm < 3.5) return false;

  const quality = observationQuality(event);
  if (quality === 'target_hint') return true;

  const resolveStatus = eventResolveStatus(event);
  const placementMode = eventPlacementMode(event);
  const coarseResolve = resolveStatus !== '' && resolveStatus !== 'ok';
  const coarsePlacement =
    placementMode === 'area' ||
    placementMode === 'region' ||
    placementMode === 'target_only_no_current_position';

  if (coarseResolve || coarsePlacement) {
    return target.confidence >= 0.7 && confidence <= Math.max(0.62, target.confidence - 0.2);
  }

  return target.confidence >= 0.8 && confidence < target.confidence - 0.25;
}

function courseTurnPenalty(target: TrackedTarget, event: CandidateEvent): number {
  const previousBearing = target.movement_vector.bearing_deg;
  if (previousBearing == null || hasSameUpstreamTrack(target, event)) return 0;
  if (target.heading_confidence === 'regional' || target.heading_confidence === 'unknown') return 0;

  const predicted = projectedTargetPosition(target, event.ts);
  const observedBearing = event.bearing_deg ?? bearingBetween(predicted.lat, predicted.lng, event.lat, event.lng);
  if (observedBearing == null) return 0;

  const dtMs = event.ts - target.last_seen;
  const timeWeight = dtMs > 15 * 60_000 ? 0.3 : dtMs > 8 * 60_000 ? 0.6 : 1.0;

  const diff = angularDiffDeg(previousBearing, observedBearing);
  if (diff > 150) return 52 * timeWeight;
  if (diff > 120) return 32 * timeWeight;
  if (diff > 90) return 20 * timeWeight;
  if (diff > 60) return 10 * timeWeight;
  return 0;
}

function courseCorridorPenalty(target: TrackedTarget, event: CandidateEvent): number {
  const previousBearing = target.movement_vector.bearing_deg;
  if (previousBearing == null || hasSameUpstreamTrack(target, event)) return 0;
  if (target.heading_confidence === 'regional' || target.heading_confidence === 'unknown') return 0;

  const dtMs = event.ts - target.last_seen;
  if (dtMs < 90_000) return 0;

  const directKm = haversineKm(target.lat, target.lng, event.lat, event.lng);
  if (directKm < 2) return 0;

  const observedFromLast = event.bearing_deg ?? bearingBetween(target.lat, target.lng, event.lat, event.lng);
  if (observedFromLast == null) return 0;

  const diff = angularDiffDeg(previousBearing, observedFromLast);
  const minutes = Math.max(0, dtMs / 60_000);
  const timeWeight = dtMs > 15 * 60_000 ? 0.4 : dtMs > 8 * 60_000 ? 0.7 : 1.0;
  const coastingWeight = (minutes >= 10 ? 1.25 : minutes >= 5 ? 1.0 : 0.75) * timeWeight;

  if (diff > 145) return 48 * coastingWeight;
  if (diff > 115) return 34 * coastingWeight;
  if (diff > 85) return 22 * coastingWeight;
  if (diff > 60) return 12 * coastingWeight;
  return 0;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function roundScore(value: number): number {
  return Math.round(value * 100) / 100;
}

function pointFromEvent(event: CandidateEvent, confidence: number, reason: string): TargetPointState {
  return {
    lat: event.lat,
    lng: event.lng,
    ts: event.ts,
    source: norm(event.source) || 'unknown',
    confidence,
    reason,
  };
}

// ─── P3-D: Time-of-flight range gate for missiles ──────────────────────────

/**
 * Returns true if the event can plausibly have arrived from the nearest known
 * threat origin within the observed time window.  Used to gate missile tracks.
 * `launchAgeMs` is how long ago the upstream track says it was first seen.
 */
function mislRangeGate(
  event: CandidateEvent,
  target: TrackedTarget,
  dtMs: number,
): boolean {
  const profile = trackMotionProfile(event.threat_type);
  if (profile.maxSpeedKmh < 400) return true; // Only apply to fast threats
  const distKm = haversineKm(target.lat, target.lng, event.lat, event.lng);
  const dtHrs = dtMs / 3_600_000;
  const maxReachableKm = profile.maxSpeedKmh * dtHrs * 1.15; // 15% margin
  return distKm <= maxReachableKm;
}

// ─── P1-B: Per-channel geo-bias table ──────────────────────────────────────

/**
 * Known systematic geocoding biases for certain upstream channel sources.
 * Key = normalised source prefix (e.g. 'channel_kyiv', 'atlas_radar').
 * Values are lat/lng offsets in degrees to ADD to measurements from that source.
 * Populated over time from worker accuracy feedback (P5-D).
 */
const CHANNEL_GEO_BIAS: Record<string, { dlat: number; dlng: number }> = {};

export function registerChannelGeoBias(source: string, dlat: number, dlng: number): void {
  CHANNEL_GEO_BIAS[source.toLowerCase()] = { dlat, dlng };
}

function applyChannelGeoBias(event: CandidateEvent): { lat: number; lng: number } {
  const src = (event.source || '').toLowerCase();
  const bias = Object.entries(CHANNEL_GEO_BIAS).find(([k]) => src.includes(k));
  if (!bias) return { lat: event.lat, lng: event.lng };
  return { lat: event.lat + bias[1].dlat, lng: event.lng + bias[1].dlng };
}

import { intersectLaunchSite } from '@/lib/launch-inference';

export class TargetTrackerEngine {
  private readonly targets = new Map<string, TrackedTarget>();
  private readonly fingerprintIndex = new Map<string, { targetId: string; seenAt: number; repostSuppressed?: boolean }>();
  /** P3-E: Ghost pool — tracks that went LOST but may re-appear */
  private readonly ghostPool = new Map<string, { target: TrackedTarget; expireAt: number }>();

  constructor(
    private readonly settings: AdminSettings,
    private readonly options: TrackerOptions = {},
  ) {
    for (const target of options.initialTargets || []) {
      this.targets.set(target.id, {
        ...target,
        count: normalizeCount(target.count),
        sources: [...target.sources],
        upstream_track_ids: [...(target.upstream_track_ids || [])],
        history: [...target.history],
        event_fingerprints: [...target.event_fingerprints],
        movement_vector: { ...target.movement_vector },
      });
      for (const fp of target.event_fingerprints) {
        this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: target.last_seen });
      }
    }
  }

  snapshot(nowMs = Date.now()): TrackedTarget[] {
    return Array.from(this.targets.values()).map((t) => ({
      ...t,
      lifecycle_state: lifecycleAt(t, nowMs),
      predicted_position: {
        ...projectedTargetPosition(t, nowMs),
        ts: normalizeEpochMs(nowMs, Date.now()),
        reason: 'motion_projection',
      },
      sources: [...t.sources],
      history: [...t.history],
      event_fingerprints: [...t.event_fingerprints],
      movement_vector: { ...t.movement_vector },
      upstream_track_ids: [...t.upstream_track_ids],
      last_observation: t.last_observation ? { ...t.last_observation } : undefined,
      last_measurement: t.last_measurement ? { ...t.last_measurement } : undefined,
      last_association: t.last_association ? { ...t.last_association } : undefined,
    }));
  }

  private forkMhtBranch(parent: TrackedTarget): TrackedTarget {
    const branch: TrackedTarget = JSON.parse(JSON.stringify({ ...parent, ekf: undefined }));
    branch.id = `mht_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`;
    branch.mht_parent_id = parent.id;
    
    if (parent.ekf) {
      if (parent.ekf instanceof IMMFilter2D) {
        branch.ekf = IMMFilter2D.fromJSON(parent.ekf.toJSON());
      } else if (parent.ekf instanceof KalmanFilter2D) {
        branch.ekf = KalmanFilter2D.fromJSON(parent.ekf.toJSON());
      }
    }
    this.targets.set(branch.id, branch);
    return branch;
  }

  ingest(event: CandidateEvent): TrackerDecision {
    const ts = normalizeEpochMs(event.ts, Date.now());
    const normalizedEvent = { ...event, ts };
    const fp = eventFingerprint(normalizedEvent);

    if (normalizedEvent.manual) {
      const created = this.createTarget(normalizedEvent, fp, 1.0, { classification: 'VERIFIED_PUBLIC', public: true, score: 1.0, scores: { extraction: 1, locality: 1, source: 1, motion: 1, evidence: 1, publication: 1 }, fingerprint: fp, reasons: ['manual'], invariantViolations: [] });
      created.manual = true;
      return { action: 'TARGET_CREATED', target: created, reason: 'manual_marker', fingerprint: fp };
    }

    this.pruneReplayIndex(ts);

    const replay = this.fingerprintIndex.get(fp);
    if (replay) {
      const target = this.targets.get(replay.targetId);
      if (target) {
        return { action: 'REPLAY_SUPPRESSED', target, reason: 'duplicate_fingerprint', fingerprint: fp };
      }
    }

    const policy = evaluateMarkerPublication(eventToPolicyMarker(normalizedEvent), { settings: this.settings, nowMs: ts });
    const eventConf = candidateConfidence(normalizedEvent);
    if (policy.classification === 'REJECTED' || eventConf < 0.4) {
      return {
        action: 'EVENT_REJECTED',
        target: null,
        reason: policy.reasons[0] || policy.invariantViolations[0] || 'low_candidate_confidence',
        fingerprint: fp,
        publication: policy,
      };
    }
    if (policy.invariantViolations.includes('unsafe_locality') || policy.invariantViolations.includes('synthetic_marker')) {
      return {
        action: 'EVENT_QUARANTINED',
        target: null,
        reason: policy.invariantViolations[0] || 'unsafe_locality',
        fingerprint: fp,
        publication: policy,
      };
    }

    const candidates = this.findAssociationCandidates(normalizedEvent, 2).filter(c => c.breakdown.accepted);
    
    if (candidates.length >= 2 && Math.abs(candidates[0].score - candidates[1].score) < 15) {
      // P6-F: MHT Branching — Create a hypothesis for the second-best candidate
      const primary = candidates[0];
      const secondary = candidates[1];
      
      const branchTarget = this.forkMhtBranch(secondary.target);
      branchTarget.mht_branch_score = secondary.score;
      this.updateTarget(branchTarget, normalizedEvent, fp, eventConf, policy, secondary.breakdown);
      
      this.updateTarget(primary.target, normalizedEvent, fp, eventConf, policy, primary.breakdown);
      return {
        action: 'TARGET_UPDATED',
        target: primary.target,
        reason: 'mht_branching',
        fingerprint: fp,
        publication: policy,
      };
    }

    const association = candidates.length > 0 ? candidates[0] : null;
    if (association) {
      const target = association.target;
      if (normalizedEvent.ts + 12_000 < target.last_seen) {
        this.appendHistory(target, normalizedEvent, fp, false, 'stale_replay', eventConf);
        target.last_measurement = pointFromEvent(normalizedEvent, eventConf, 'stale_replay');
        target.last_association = { ...association.breakdown, accepted: false, reason: 'stale_replay' };
        // P1-D: Do NOT index stale-replay fingerprints permanently. A future valid event
        // from a different channel with the same fingerprint should not be silently suppressed.
        // We only record it transiently (not in fingerprintIndex) so de-dup within one ingest
        // cycle works, but cross-channel valid events are not blocked for the full 6h window.
        return {
          action: 'EVENT_QUARANTINED',
          target,
          reason: 'stale_replay',
          fingerprint: fp,
          publication: policy,
        };
      }

      const movement = impossibleMovement(target, normalizedEvent);
      // Same-chain events may have large coordinate jumps due to trajectory recalculation
      // (e.g. maritime approach: the sea→target fraction changes between worker messages).
      // Trust the updated position rather than quarantining as impossible movement.
      if (movement.impossible && !association.breakdown.same_upstream_track) {
        this.appendHistory(target, normalizedEvent, fp, false, 'impossible_movement', eventConf);
        target.last_measurement = pointFromEvent(normalizedEvent, eventConf, 'impossible_movement');
        target.last_association = { ...association.breakdown, accepted: false, reason: 'impossible_movement' };
        target.lifecycle_state = target.confidence >= 0.4 ? 'TRACKING' : 'DETECTED';
        this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: ts });
        return {
          action: 'EVENT_QUARANTINED',
          target,
          reason: 'impossible_movement',
          fingerprint: fp,
          publication: policy,
        };
      }
      this.updateTarget(target, normalizedEvent, fp, eventConf, policy, association.breakdown);
      return {
        action: 'TARGET_UPDATED',
        target,
        reason: 'associated',
        fingerprint: fp,
        publication: policy,
      };
    }

    const impossibleTarget = this.findImpossibleMovementCandidate(normalizedEvent);
    if (impossibleTarget) {
      this.appendHistory(impossibleTarget, normalizedEvent, fp, false, 'impossible_movement', eventConf);
      impossibleTarget.last_measurement = pointFromEvent(normalizedEvent, eventConf, 'impossible_movement');
      impossibleTarget.last_association = {
        score: 0,
        threshold: ASSOCIATION_SCORE_MIN,
        distance_km: round1(haversineKm(impossibleTarget.lat, impossibleTarget.lng, normalizedEvent.lat, normalizedEvent.lng)),
        radius_km: round1(maxAssociationRadius(normalizedEvent, this.options, impossibleTarget)),
        same_place: Boolean(impossibleTarget.place && normalizedEvent.place && norm(impossibleTarget.place) === norm(normalizedEvent.place)),
        same_upstream_track: hasSameUpstreamTrack(impossibleTarget, normalizedEvent),
        count_penalty: 0,
        bearing_penalty: 0,
        corridor_penalty: 0,
        innovation_penalty: 0,
        accepted: false,
        reason: 'impossible_movement',
      };
      impossibleTarget.lifecycle_state = impossibleTarget.confidence >= 0.4 ? 'TRACKING' : 'DETECTED';
      this.fingerprintIndex.set(fp, { targetId: impossibleTarget.id, seenAt: ts });
      return {
        action: 'EVENT_QUARANTINED',
        target: impossibleTarget,
        reason: 'impossible_movement',
        fingerprint: fp,
        publication: policy,
      };
    }

    // P3-E: Try ghost pool handoff before creating a new track
    const ghostTarget = this.tryGhostPoolHandoff(normalizedEvent, ts);
    if (ghostTarget) {
      this.updateTarget(ghostTarget, normalizedEvent, fp, eventConf, policy, {
        score: 90,
        threshold: ASSOCIATION_SCORE_MIN,
        distance_km: 0,
        radius_km: 25,
        same_place: false,
        same_upstream_track: false,
        count_penalty: 0,
        bearing_penalty: 0,
        corridor_penalty: 0,
        innovation_penalty: 0,
        accepted: true,
        reason: 'ghost_pool_handoff',
      });
      return {
        action: 'TARGET_UPDATED',
        target: ghostTarget,
        reason: 'ghost_pool_handoff',
        fingerprint: fp,
        publication: policy,
      };
    }

    const splitParent = this.findSplitParent(normalizedEvent);
    if (splitParent) {
      const created = this.createSplitTarget(splitParent, normalizedEvent, fp, eventConf, policy);
      return {
        action: 'TARGET_CREATED',
        target: created,
        reason: 'swarm_split',
        fingerprint: fp,
        publication: policy,
      };
    }

    const created = this.createTarget(normalizedEvent, fp, eventConf, policy);
    if (created.confidence >= 0.4) {
      // Deduplicate immediately in case two near-simultaneous events created overlapping targets
      this.detectAndMergeDuplicates(ts);
    }
    const action = created.confidence >= 0.4 ? 'TARGET_CREATED' : 'EVENT_QUARANTINED';
    return {
      action,
      target: created,
      reason: action === 'TARGET_CREATED' ? 'new_target' : 'low_candidate_confidence',
      fingerprint: fp,
      publication: policy,
    };
  }

  markLifecycle(targetId: string, state: TargetLifecycleState, nowMs = Date.now()): TrackedTarget | null {
    const target = this.targets.get(targetId);
    if (!target) return null;
    target.lifecycle_state = state;
    target.last_seen = normalizeEpochMs(nowMs, Date.now());
    return target;
  }

  private findAssociation(event: CandidateEvent): { target: TrackedTarget; breakdown: TargetAssociationBreakdown } | null {
    const eventCount = normalizeCount(event.count);
    const quality = observationQuality(event);
    const textIntent = inferTextIntent(event);
    let best: { target: TrackedTarget; score: number; breakdown: TargetAssociationBreakdown } | null = null;
    for (const target of this.targets.values()) {
      if (norm(target.threat_type) !== norm(event.threat_type)) continue;
      const currentLifecycle = lifecycleAt(target, event.ts);
      if (currentLifecycle === 'LOST' || currentLifecycle === 'DESTROYED' || currentLifecycle === 'REJECTED') {
        continue;
      }
      const sameUpstreamTrack = hasSameUpstreamTrack(target, event);
      if (hasDifferentExplicitGroup(target, event)) continue;
      if (
        !sameUpstreamTrack &&
        target.count > 1 &&
        eventCount < target.count &&
        target.count - eventCount >= 2 &&
        eventCount <= Math.ceil(target.count * 0.7)
      ) {
        continue;
      }
      const sameRegion = Boolean(target.region && event.region && norm(target.region) === norm(event.region));
      if (
        target.region &&
        event.region &&
        !sameRegion &&
        !sameUpstreamTrack
      ) continue;
      // Per-target adaptive radius (young targets get tighter radius)
      let radiusKm = maxAssociationRadius(event, this.options, target);
      if (sameUpstreamTrack) {
        const profile = trackMotionProfile(event.threat_type);
        const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 0);
        const trackIdMotionBudgetKm = Math.max(25, profile.nominalSpeedKmh * dtHours * 1.65);
        radiusKm = Math.min(90, Math.max(radiusKm, trackIdMotionBudgetKm));
      }
      // P4-A: EKF sigma gate — tighten radius when filter is confident
      if (target.ekf) {
        const sigmaKm = target.ekf.positionSigmaKm();
        const ekfGateKm = Math.max(5, sigmaKm * 3);
        // Tighten toward 3σ when confident, never below 5 km, never above default radius
        radiusKm = Math.min(radiusKm, Math.max(5, ekfGateKm));
      }
      const predicted = projectedTargetPosition(target, event.ts);
      const pointDist = haversineKm(predicted.lat, predicted.lng, event.lat, event.lng);
      const corridorDist = predicted.projected
        ? segmentDistanceKm(target.lat, target.lng, predicted.lat, predicted.lng, event.lat, event.lng)
        : pointDist;
      const dist = Math.min(pointDist, corridorDist);
      if (dist > radiusKm) {
        continue;
      }
      const samePlace = target.place && event.place && norm(target.place) === norm(event.place);
      const countPenalty = target.count !== eventCount ? Math.min(18, Math.abs(target.count - eventCount) * 6) : 0;
      // Bearing penalty: threats moving in opposite directions should not merge
      const bearingPenalty = courseTurnPenalty(target, event);
      const corridorPenalty = courseCorridorPenalty(target, event);
      const innovationPenalty = movementInnovationPenalty(target, event, dist);
      const qualityPenalty = qualityAssociationPenalty(quality, sameUpstreamTrack, !!samePlace);
      const groupBonus = groupAssociationBonus(textIntent, target, event);
      // P4-D: Hard bearing reject — if the target has a confident heading and the
      // observed event is moving in the opposite direction, reject the association
      // regardless of score.  Only applies at speed > 50 km/h with good confidence.
      if (
        !sameUpstreamTrack &&
        target.heading_confidence !== 'regional' &&
        target.heading_confidence !== 'unknown' &&
        target.movement_vector.bearing_deg != null &&
        event.bearing_deg != null &&
        target.speed_estimate_kmh != null &&
        target.speed_estimate_kmh > 50 &&
        candidateConfidence(event) > 0.6
      ) {
        const bearingDelta = angularDiffDeg(target.movement_vector.bearing_deg, event.bearing_deg);
        if (bearingDelta > 120) continue;
      }

      // P1-B: Observation density bonus — prefer tracks with more accepted observations.
      // log1p(n) grows quickly for first few obs then levels off, max bonus ≈ 12 pts.
      const acceptedObs = target.history.filter((h) => h.accepted).length;
      const densityBonus = Math.min(12, Math.log1p(acceptedObs) * 2.5);

      const score = 100
        - (dist / radiusKm) * 65
        + (samePlace ? 12 : 0)
        + (sameRegion ? 4 : 0)
        + (sameUpstreamTrack ? 25 : 0)
        + densityBonus
        + groupBonus
        - countPenalty
        - bearingPenalty
        - corridorPenalty
        - innovationPenalty
        - qualityPenalty;
      
      const threshold = associationScoreThreshold(target, event, !!samePlace);
      const breakdown: TargetAssociationBreakdown = {
        score: roundScore(score),
        threshold,
        distance_km: round1(dist),
        radius_km: round1(radiusKm),
        same_place: !!samePlace,
        same_upstream_track: sameUpstreamTrack,
        count_penalty: roundScore(countPenalty),
        bearing_penalty: roundScore(bearingPenalty),
        corridor_penalty: roundScore(corridorPenalty),
        innovation_penalty: roundScore(innovationPenalty),
        quality_penalty: roundScore(qualityPenalty),
        group_bonus: roundScore(groupBonus),
        text_intent: textIntent,
        observation_quality: quality,
        accepted: score >= threshold,
        reason: score >= threshold ? 'associated' : 'score_below_threshold',
      };
      if (score < threshold) {
        continue;
      }
      // P2-C: Tie-break by score desc, then older track first (more observations = prefer), then closer dist.
      if (
        !best ||
        score > best.score ||
        (score === best.score && target.first_seen < best.target.first_seen) ||
        (score === best.score && target.first_seen === best.target.first_seen && dist < best.breakdown.distance_km)
      ) {
        best = { target, score, breakdown };
      }
    }
    return best ? { target: best.target, breakdown: best.breakdown } : null;
  }

  private findImpossibleMovementCandidate(event: CandidateEvent): TrackedTarget | null {
    let nearest: { target: TrackedTarget; distKm: number } | null = null;
    for (const target of this.targets.values()) {
      if (norm(target.threat_type) !== norm(event.threat_type)) continue;
      const currentLifecycle = lifecycleAt(target, event.ts);
      if (currentLifecycle === 'LOST' || currentLifecycle === 'DESTROYED' || currentLifecycle === 'REJECTED') continue;
      if (target.region && event.region && norm(target.region) !== norm(event.region)) continue;

      const movement = impossibleMovement(target, event);
      if (!movement.impossible) continue;
      const relaxedRadiusKm = maxAssociationRadius(event, this.options) * 1.15;
      if (movement.distKm > relaxedRadiusKm) continue;
      if (!nearest || movement.distKm < nearest.distKm) {
        nearest = { target, distKm: movement.distKm };
      }
    }
    return nearest?.target ?? null;
  }

  private findSplitParent(event: CandidateEvent): TrackedTarget | null {
    let best: { target: TrackedTarget; distKm: number } | null = null;
    // P2-D: Use threat-type velocity to determine plausible split radius.
    // A missile can travel 100+ km in 5 min; an FPV stays within 3 km.
    // Lookback window: 5 minutes of nominal motion budget, clamped [10, 80] km.
    const profile = trackMotionProfile(event.threat_type);
    const splitRadiusKm = Math.min(80, Math.max(10, profile.nominalSpeedKmh * (5 / 60)));

    for (const target of this.targets.values()) {
      if (norm(target.threat_type) !== norm(event.threat_type)) continue;
      const currentLifecycle = lifecycleAt(target, event.ts);
      if (currentLifecycle === 'LOST' || currentLifecycle === 'DESTROYED' || currentLifecycle === 'REJECTED') {
        continue;
      }

      // If it's the same upstream track, it's not a split (should have been associated)
      if (hasSameUpstreamTrack(target, event)) continue;

      const dist = haversineKm(target.lat, target.lng, event.lat, event.lng);
      if (dist < splitRadiusKm) {
        if (!best || dist < best.distKm) {
          best = { target, distKm: dist };
        }
      }
    }
    return best?.target ?? null;
  }

  private createTarget(
    event: CandidateEvent,
    fp: string,
    confidence: number,
    publication: MarkerPublicationDecision,
  ): TrackedTarget {
    const biased = applyChannelGeoBias(event);
    const correctedEvent = { ...event, lat: biased.lat, lng: biased.lng };
    event = correctedEvent;
    const source = norm(event.source) || 'unknown';
    const upstreamTrackId = normalizeTrackId(event.upstream_track_id);
    const target: TrackedTarget = {
      id: targetIdForNewEvent(event, fp, this.targets),
      threat_type: event.threat_type,
      region: event.region,
      place: event.place,
      lat: event.lat,
      lng: event.lng,
      count: normalizeCount(event.count),
      confidence,
      reliability: sourceReliability(event),
      source_count: 1,
      sources: [source],
      upstream_track_ids: upstreamTrackId ? [upstreamTrackId] : [],
      lifecycle_state: 'DETECTED',
      first_seen: event.ts,
      last_seen: event.ts,
      movement_vector: { bearing_deg: event.bearing_deg ?? null, speed_kmh: null },
      speed_estimate_kmh: null,
      history: [],
      event_fingerprints: [],
      publication,
      last_observation: pointFromEvent(event, confidence, 'created'),
      predicted_position: { lat: event.lat, lng: event.lng, ts: event.ts, reason: 'created' },
      last_measurement: pointFromEvent(event, confidence, 'created'),
      last_association: {
        score: 100,
        threshold: 0,
        distance_km: 0,
        radius_km: 0,
        same_place: true,
        same_upstream_track: Boolean(upstreamTrackId),
        count_penalty: 0,
        bearing_penalty: 0,
        corridor_penalty: 0,
        innovation_penalty: 0,
        quality_penalty: 0,
        group_bonus: 0,
        text_intent: inferTextIntent(event),
        observation_quality: observationQuality(event),
        accepted: true,
        reason: 'created',
      },
      last_message_text: typeof event.raw?.text === 'string' ? event.raw.text : undefined,
      last_resolve_status: typeof event.raw?.resolve_status === 'string' ? event.raw.resolve_status : undefined,
      last_placement_mode: typeof event.raw?.placement_mode === 'string' ? event.raw.placement_mode : undefined,
      last_observation_quality: observationQuality(event),
      last_text_intent: inferTextIntent(event),
      ekf: ['missile', 'fpv', 'raketa', 'krylata', 'pusk'].includes(event.threat_type) ?
        new IMMFilter2D(
          event.lat,
          event.lng,
          trackMotionProfile(event.threat_type).ekfProcessNoise * 0.5,
          trackMotionProfile(event.threat_type).ekfProcessNoise * 5,
          trackMotionProfile(event.threat_type).ekfMeasurementNoise,
          0.05
        ) :
        new KalmanFilter2D(
          event.lat, 
          event.lng, 
          0, // Start at rest, learn speed from subsequent observations
          event.bearing_deg ?? 0, 
          0.1,  // initialPosCov
          1e-4, // initialVelCov (low trust until motion is observed)
          trackMotionProfile(event.threat_type).ekfProcessNoise,
          trackMotionProfile(event.threat_type).ekfMeasurementNoise,
        ),
    };
    target.lifecycle_state = lifecycleFor(target, publication);
    this.appendHistory(target, event, fp, true, 'created', confidence);
    this.targets.set(target.id, target);
    this.assignSwarmCluster(target);
    this._applyRendering(target);
    this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: event.ts });
    return target;
  }

  private updateTarget(
    target: TrackedTarget,
    event: CandidateEvent,
    fp: string,
    confidence: number,
    publication: MarkerPublicationDecision,
    association: TargetAssociationBreakdown,
  ): void {
    // P1-B: apply per-channel geo bias correction
    const biased = applyChannelGeoBias(event);
    event = { ...event, lat: biased.lat, lng: biased.lng };

    const prevLat = target.lat;
    const prevLng = target.lng;
    const predicted = projectedTargetPosition(target, event.ts);
    const priorLat = predicted.lat;
    const priorLng = predicted.lng;
    const rawDist = haversineKm(priorLat, priorLng, event.lat, event.lng);
    const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 1 / 3600);
    const holdPosition = shouldHoldWeakMeasurement(target, event, confidence, rawDist);
    const alpha = holdPosition ? 0 : measurementBlendAlpha(target, event, confidence, rawDist);
    const nextLat = holdPosition ? prevLat : rawDist > 0.35 ? blendCoordinate(priorLat, event.lat, alpha) : event.lat;
    const nextLng = holdPosition ? prevLng : rawDist > 0.35 ? blendCoordinate(priorLng, event.lng, alpha) : event.lng;
    const smoothedDist = haversineKm(prevLat, prevLng, nextLat, nextLng);
    const observedSpeed = smoothedDist > 1 ? smoothedDist / dtHours : target.speed_estimate_kmh;
    const previousSpeed = target.speed_estimate_kmh;
    const speed = observedSpeed != null && Number.isFinite(observedSpeed)
      ? previousSpeed != null && Number.isFinite(previousSpeed)
        ? previousSpeed * 0.45 + observedSpeed * 0.55
        : observedSpeed
      : previousSpeed;
    const observedBearing = holdPosition ? null : event.bearing_deg ?? (
      smoothedDist > 0.2 ? bearingBetween(prevLat, prevLng, nextLat, nextLng) : null
    );
    const priorHeadingWeak = target.heading_confidence === 'regional' || target.heading_confidence === 'unknown';
    const bearingAlpha = priorHeadingWeak
      ? 0.75
      : event.bearing_deg != null
      ? 0.55
      : hasSameUpstreamTrack(target, event)
        ? 0.45
        : 0.32;
    const bearing = blendBearingDeg(target.movement_vector.bearing_deg, observedBearing, bearingAlpha);
    const source = norm(event.source) || 'unknown';
    const sources = new Set(target.sources);
    sources.add(source);
    const upstreamTrackId = normalizeTrackId(event.upstream_track_id);
    if (upstreamTrackId && !target.upstream_track_ids.includes(upstreamTrackId)) {
      target.upstream_track_ids = [...target.upstream_track_ids, upstreamTrackId].sort();
    }

    if (target.ekf && !holdPosition) {
      const elapsedSec = (event.ts - target.last_seen) / 1000;

      // P1-D: Retroactive EKF re-origin when filter has diverged too far from measurement.
      // If singularSkipCount is high AND the position is >2σ from the current state, reset.
      const preDivergeDist = haversineKm(target.ekf.lat, target.ekf.lng, event.lat, event.lng);
      if (target.ekf.singularSkipCount >= 3 && preDivergeDist > target.ekf.positionSigmaKm() * 2.5) {
        // Re-initialise EKF at the new measurement, preserving velocity and process noise
        target.ekf.resetPosition(event.lat, event.lng);
      }

      target.ekf.predict(elapsedSec);

      // P2-E: For maritime_approach / estimated placements, only update position components
      // to prevent the indirect (fraction-interpolated) coordinate from corrupting velocity state.
      const isMaritimeEstimate =
        target.last_resolve_status === 'maritime_approach' ||
        target.last_resolve_status === 'estimated_trajectory' ||
        target.last_placement_mode === 'fraction';

      // P5-D: pass channel priority so high-priority channels get tighter measurement noise
      const chPriority = Number.isFinite(Number(event.channel_priority)) ? Number(event.channel_priority) : undefined;
      if (isMaritimeEstimate) {
        target.ekf.updatePositionOnly(event.lat, event.lng, confidence);
      } else {
        target.ekf.update(event.lat, event.lng, confidence, chPriority, event.sensor_type);
      }

      // Swarm "Soft Gravity"
      if (target.swarm_cluster_id && !isMaritimeEstimate) {
        for (const other of this.targets.values()) {
          if (other.id !== target.id && other.swarm_cluster_id === target.swarm_cluster_id && other.ekf) {
            // Pull other members slightly towards this new measurement (confidence=0.05)
            other.ekf.updatePositionOnly(event.lat, event.lng, 0.05);
            other.lat = other.ekf.lat;
            other.lng = other.ekf.lng;
          }
        }
      }

      // P2-B: Jerk / maneuver detection — compute acceleration magnitude from EKF velocity change
      const prevVx = 'state' in target.ekf ? (target.ekf as KalmanFilter2D).state[2] : 0;
      const prevVy = 'state' in target.ekf ? (target.ekf as KalmanFilter2D).state[3] : 0;

      target.lat = target.ekf.lat;
      target.lng = target.ekf.lng;
      // Use metric helpers for correct cos(lat)-aware speed and bearing
      const ekfSpeedKmh = Math.round(target.ekf.speedKmh());
      const ekfBearingDeg = Math.round(target.ekf.bearingDeg());

      // Compute jerk signal: change in velocity over time
      if (elapsedSec > 0) {
        // P7-F: Wind Vector Modeling - calculate Air Speed vs Ground Speed
        const profile = trackMotionProfile(target.threat_type);
        const altitude = profile.nominalAltitudeMeters || 500;
        const wind = getWindVector(target.lat, target.lng, altitude);
        
        // Ground speed components
        const gvx = 'state' in target.ekf ? (target.ekf as KalmanFilter2D).state[2] : 0;
        const gvy = 'state' in target.ekf ? (target.ekf as KalmanFilter2D).state[3] : 0;
        
        // Air speed components (Air = Ground - Wind)
        const cosLat = Math.cos((target.lat * Math.PI) / 180);
        const gvx_ms = gvx * 111320;
        const gvy_ms = gvy * cosLat * 111320;
        
        const avx_ms = gvx_ms - wind.vx;
        const avy_ms = gvy_ms - wind.vy;
        target.air_speed_kmh = Math.round(Math.sqrt(avx_ms ** 2 + avy_ms ** 2) * 3.6);

        if (target.ekf.maneuverWeight > 0.35) {
          target.maneuver_detected = true;
        } else if ('state' in target.ekf) {
          const kf = target.ekf as KalmanFilter2D;
          const dvx = Math.abs(kf.state[2] - prevVx);
          const dvy = Math.abs(kf.state[3] - prevVy);
          const jerkDegPerSecSq = Math.sqrt(dvx * dvx + dvy * dvy) / elapsedSec;
          const jerkThreshold = (profile.maxSpeedKmh / 3600 / 111320) * 0.15;
          target.maneuver_detected = jerkDegPerSecSq > jerkThreshold && kf.singularSkipCount < 3;
        } else {
          target.maneuver_detected = false;
        }
      }

      target.speed_estimate_kmh = ekfSpeedKmh;
      target.movement_vector = { bearing_deg: ekfBearingDeg, speed_kmh: ekfSpeedKmh };
    } else {
      target.lat = nextLat;
      target.lng = nextLng;
      target.speed_estimate_kmh = speed != null && Number.isFinite(speed) ? Math.round(speed) : null;
      target.movement_vector = {
        bearing_deg: bearing != null && Number.isFinite(bearing) ? Math.round(bearing) : null,
        speed_kmh: target.speed_estimate_kmh,
      };
    }

    target.count = Math.max(normalizeCount(target.count), normalizeCount(event.count));
    target.place = holdPosition ? target.place : event.place || target.place;
    target.region = event.region || target.region;
    target.last_seen = event.ts;
    target.sources = Array.from(sources).sort();
    target.source_count = target.sources.length;
    target.reliability = Math.max(target.reliability, sourceReliability(event));
    target.confidence = clamp01(Math.max(target.confidence, confidence) + Math.min(0.12, target.source_count * 0.025));
    if (
      target.source_count >= 2 &&
      target.confidence >= 0.7 &&
      target.reliability >= 0.85 &&
      !publication.invariantViolations.includes('unsafe_locality') &&
      !publication.invariantViolations.includes('synthetic_marker') &&
      publication.classification !== 'REJECTED'
    ) {
      target.confidence = Math.max(target.confidence, 0.95);
    }
    target.publication = publication;
    // P4-D: Keep a rolling window of the last 5 publication decisions for admin/audit display.
    const pubEntry = {
      ts: event.ts,
      public: publication.public ?? false,
      classification: publication.classification,
      reason: publication.reasons[0] || publication.invariantViolations[0] || 'evaluated',
    };
    if (!target.publication_history) target.publication_history = [];
    target.publication_history.push(pubEntry);
    if (target.publication_history.length > 5) target.publication_history.shift();
    target.last_measurement = pointFromEvent(event, confidence, holdPosition ? 'measurement_held' : 'measurement_accepted');
    target.last_observation = {
      lat: target.lat,
      lng: target.lng,
      ts: event.ts,
      source,
      confidence,
      reason: holdPosition ? 'position_held' : 'fused_update',
    };
    target.last_association = {
      ...association,
      accepted: true,
      reason: holdPosition ? 'associated_position_held' : 'associated',
    };
    if (typeof event.raw?.text === 'string') target.last_message_text = event.raw.text;
    if (typeof event.raw?.resolve_status === 'string') target.last_resolve_status = event.raw.resolve_status;
    if (typeof event.raw?.placement_mode === 'string') target.last_placement_mode = event.raw.placement_mode;
    target.last_observation_quality = observationQuality(event);
    target.last_text_intent = inferTextIntent(event);
    target.lifecycle_state = lifecycleFor(target, publication);
    this.appendHistory(target, event, fp, true, holdPosition ? 'updated_position_held' : 'updated', confidence);

    // P1-C: Burst score — ratio of events in the last 5 min vs average over track lifetime.
    // A score > 0.7 indicates a burst (rapid successive reports of same target).
    {
      const BURST_WINDOW_MS = 5 * 60_000;
      const recentCount = target.history.filter((h) => h.accepted && event.ts - h.ts < BURST_WINDOW_MS).length;
      const ageMin = Math.max(1, (event.ts - target.first_seen) / 60_000);
      const totalAccepted = target.history.filter((h) => h.accepted).length;
      const avgPerMin = totalAccepted / ageMin;
      const recentPerMin = recentCount / (BURST_WINDOW_MS / 60_000);
      const burstRatio = avgPerMin > 0 ? recentPerMin / Math.max(avgPerMin, 0.1) : recentPerMin;
      target.burst_score = Math.round(Math.min(1, burstRatio / 3) * 100) / 100;
    }

    // P1-E: Threat-type morphing detection — track if the threat type has changed.
    if (event.threat_type && event.threat_type !== target.threat_type) {
      if (!target.threat_type_history) target.threat_type_history = [];
      if (!target.threat_type_history.includes(target.threat_type)) {
        target.threat_type_history.push(target.threat_type);
      }
    }

    this._applyRendering(target);
    this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: event.ts });
  }

  private appendHistory(
    target: TrackedTarget,
    event: CandidateEvent,
    fp: string,
    accepted: boolean,
    reason: string,
    confidence: number,
  ): void {
    const channelPriority = Number.isFinite(Number(event.channel_priority)) ? Number(event.channel_priority) : undefined;
    const count = normalizeCount(event.count);
    const messageText = typeof event.raw?.text === 'string' && event.raw.text.length > 0 ? event.raw.text : undefined;
    target.history.push({
      fingerprint: fp,
      ts: event.ts,
      lat: event.lat,
      lng: event.lng,
      source: norm(event.source) || 'unknown',
      ...(channelPriority !== undefined && { channel_priority: channelPriority }),
      ...(count > 1 && { count }),
      ...(messageText !== undefined && { message_text: messageText }),
      accepted,
      reason,
      confidence,
    });
    target.event_fingerprints.push(fp);
    const maxHistory = this.options.maxHistory ?? DEFAULT_MAX_HISTORY;
    if (target.history.length > maxHistory) target.history.splice(0, target.history.length - maxHistory);
    if (target.event_fingerprints.length > maxHistory) {
      target.event_fingerprints.splice(0, target.event_fingerprints.length - maxHistory);
    }
  }

  updateTargetAdministrative(targetId: string, updates: Record<string, unknown>): boolean {
    const target = this.targets.get(targetId);
    if (!target) return false;

    if (updates.lat !== undefined) target.lat = Number(updates.lat);
    if (updates.lng !== undefined) target.lng = Number(updates.lng);
    if (updates.count !== undefined) target.count = normalizeCount(updates.count);
    if (updates.threat_type !== undefined) target.threat_type = String(updates.threat_type);
    if (updates.place !== undefined) target.place = String(updates.place);
    if (updates.region !== undefined) target.region = String(updates.region);
    if (updates.course_bearing !== undefined) {
      target.movement_vector.bearing_deg = Number(updates.course_bearing);
    }
    if (updates.speed_kmh !== undefined) {
      target.speed_estimate_kmh = Number(updates.speed_kmh);
      target.movement_vector.speed_kmh = Number(updates.speed_kmh);
    }
    if (updates.manual !== undefined) target.manual = !!updates.manual;
    
    target.last_seen = Date.now();
    return true;
  }

  private pruneReplayIndex(nowMs: number): void {
    const ttl = this.options.replayWindowMs ?? DEFAULT_REPLAY_WINDOW_MS;
    for (const [fp, item] of this.fingerprintIndex.entries()) {
      if (nowMs - item.seenAt > ttl) this.fingerprintIndex.delete(fp);
    }
  }

  /**
   * Run the drone-tracker renderer after every create/update.
   * Builds a RendererEvent from the target's current state + history,
   * then writes is_loitering, heading_confidence, position_estimated,
   * eta_seconds, display_confidence (and optionally rendered_lat/lng)
   * back onto the target so they flow through the store → marker → map.
   */
  private _applyRendering(target: TrackedTarget): void {
    try {
      // Build prev_events from history (oldest first, skip last = current)
      const hist = target.history.slice(0, -1);
      const prevEvents: RendererEvent[] = hist.map((h) => ({
        track_id: target.id,
        marker_id: h.fingerprint,
        coords: [h.lat, h.lng] as [number, number],
        place: target.place || '',
        region: target.region || null,
        speed_kmh: target.speed_estimate_kmh || 170,
        confidence: h.confidence * 100,
        resolve: 'ok' as const,
        message_text: '',
        timestamp: new Date(h.ts > 1e10 ? h.ts : h.ts * 1000).toISOString(),
        prev_events: [],
      }));

      // Current event from the latest history item
      const latest = target.history[target.history.length - 1];
      if (!latest) return;

      // Resolve the resolve_status from the raw event if available
      const resolveStatus = target.last_resolve_status;
      const resolveType = (
        resolveStatus === 'direction_geocode_fallback' ? 'direction_geocode_fallback'
        : resolveStatus === 'area_center' || resolveStatus === 'oblast_direction_only' || resolveStatus === 'regional_oblast_centroid' ? 'area_center'
        : resolveStatus === 'regional_oblast_direction_target' || resolveStatus === 'oblast_fallback' ? 'region_centroid'
        : resolveStatus === 'ambiguous_no_point' || resolveStatus === 'failed' ? 'failed'
        : 'ok'
      ) as RendererEvent['resolve'];

      // message_text may be stored in raw event data
      const rawText = target.last_message_text || '';

      const currentEvent: RendererEvent = {
        track_id: target.id,
        marker_id: latest.fingerprint,
        coords: [latest.lat, latest.lng] as [number, number],
        place: target.place || '',
        region: target.region || null,
        speed_kmh: target.speed_estimate_kmh || 170,
        confidence: target.confidence * 100,
        resolve: resolveType,
        message_text: rawText,
        timestamp: new Date(latest.ts > 1e10 ? latest.ts : latest.ts * 1000).toISOString(),
        prev_events: prevEvents,
        threat_type: target.threat_type,
      };

      const desc = buildTrackerRenderDescriptor(currentEvent);

      target.is_loitering = desc.is_loitering;
      target.heading_confidence = desc.heading_confidence;
      target.position_estimated = desc.position_estimated ?? false;
      target.eta_seconds = desc.eta_seconds;
      target.display_confidence = desc.display_confidence;

      // P3-A: Wire trail and target destination from renderer into TrackedTarget.
      // These flow through targetToStoreRecord → mapStoreRecordToMarker for map display.
      target.tracker_trail = desc.trail.length > 0 ? desc.trail : undefined;
      target.tracker_target = desc.target;

      // Only override lat/lng if the renderer produced a meaningfully different
      // position (back-projection) AND the resolve is not 'ok' (direct observation).
      // For 'ok' resolves we trust the geocoded coords directly.
      if (
        desc.position_estimated &&
        resolveType !== 'ok' &&
        Number.isFinite(desc.position[0]) &&
        Number.isFinite(desc.position[1])
      ) {
        target.rendered_lat = desc.position[0];
        target.rendered_lng = desc.position[1];
      } else {
        target.rendered_lat = undefined;
        target.rendered_lng = undefined;
      }

      // If heading_confidence is 'track' or 'explicit' and no bearing yet, apply it
      if (
        desc.heading_deg != null &&
        target.movement_vector.bearing_deg == null
      ) {
        target.movement_vector.bearing_deg = Math.round(desc.heading_deg);
      }

      // P1-D: Maritime bearing fix — when a maritime_approach track has a known target
      // city (tracker_target) and the renderer hasn't established a track bearing yet,
      // compute the direct bearing from current position to the target city.
      if (
        target.last_resolve_status === 'maritime_approach' &&
        target.tracker_target &&
        (target.heading_confidence === 'regional' || target.heading_confidence === 'unknown') &&
        target.movement_vector.bearing_deg == null
      ) {
        const [tgtLat, tgtLng] = target.tracker_target;
        const directBearing = bearingBetween(target.lat, target.lng, tgtLat, tgtLng);
        if (directBearing != null) {
          target.movement_vector.bearing_deg = Math.round(directBearing);
        }
      }

      // P2-A: Improved ETA — use EKF velocity when available for more precise estimate.
      // The renderer may set eta_seconds; supplement with direct velocity calculation.
      if (target.tracker_target) {
        const [tgtLat, tgtLng] = target.tracker_target;
        const distToTargetKm = haversineKm(target.lat, target.lng, tgtLat, tgtLng);
        const speedKmh = target.ekf
          ? target.ekf.speedKmh()
          : target.speed_estimate_kmh ?? trackMotionProfile(target.threat_type).nominalSpeedKmh;
        if (speedKmh > 0 && Number.isFinite(speedKmh)) {
          const etaSeconds = Math.round((distToTargetKm / speedKmh) * 3600);
          // Only override if not already set by renderer, or if ours is more precise (EKF-based)
          if (typeof target.eta_seconds !== 'number' || target.ekf) {
            target.eta_seconds = etaSeconds > 0 ? etaSeconds : null;
          }

          // P2-C: Probabilistic ETA — Monte Carlo p10/p50/p90 using EKF speed uncertainty.
          // Speed uncertainty is estimated as ±20% of nominal speed for non-EKF tracks,
          // or derived from EKF process noise otherwise.
          const profile = trackMotionProfile(target.threat_type);
          const speedUncertaintyFrac = target.ekf
            ? Math.min(0.4, Math.sqrt(target.ekf.qProcessNoise) * 1e4)
            : 0.2;
          const speedSigma = speedKmh * speedUncertaintyFrac;
          // p10: slower end (higher ETA), p90: faster end (lower ETA)
          const speedP10 = Math.max(10, speedKmh - speedSigma * 1.28);
          const speedP90 = Math.min(profile.maxSpeedKmh, speedKmh + speedSigma * 1.28);
          target.eta_p10 = speedP10 > 0 ? Math.round((distToTargetKm / speedP10) * 3600) : null;
          target.eta_p90 = speedP90 > 0 ? Math.round((distToTargetKm / speedP90) * 3600) : null;
        }
      }

      // P5-E: Trajectory confidence — propagate from event data + compute from track quality.
      if (typeof target.trajectory_confidence !== 'number') {
        const obsCount = target.history.filter((h) => h.accepted).length;
        const ekfPenalty = target.ekf ? (target.ekf.singularSkipCount > 2 ? 0.2 : 0) : 0.1;
        const baseConf = Math.min(0.95, 0.4 + obsCount * 0.06);
        target.trajectory_confidence = Math.max(0.1, baseConf - ekfPenalty);
      }

      // P3-B: Sea-to-land transition — detect when a maritime track crosses the coastline.
      // A track is "coastal_transition" if its previous position was maritime (lat < 46.5,
      // Black/Azov Sea bbox) and current position is on land (lat > 45.8, within UA bounds).
      if (target.last_resolve_status === 'maritime_approach' || target.coastal_transition) {
        const prevObs = target.history.slice(-3, -1).filter((h) => h.accepted);
        if (prevObs.length > 0) {
          const prevLat = prevObs[prevObs.length - 1]!.lat;
          const prevLng = prevObs[prevObs.length - 1]!.lng;
          const wasAtSea = prevLat < 46.5 && prevLng > 30 && prevLng < 37;
          const isOnLand = target.lat > 45.8 && target.lat < 52 && target.lng > 22 && target.lng < 40;
          target.coastal_transition = wasAtSea && isOnLand;
        }
      }

      // P3-E: Altitude inference — classify flight mode from message text keywords.
      if (target.last_message_text) {
        const txt = target.last_message_text.toLowerCase();
        if (/балістич|ракет|хвиля|гіперзвук|зенітн|мрлс|пуск|rpl|б-21|б-52|р-500|р-360|9м729/i.test(txt)) {
          target.altitude_mode = 'ballistic_arc';
        } else if (/бпла|дрон|fpv|shahed|shahid|шахед|герань|ланцет|мавік|mavic|orlan|орлан/i.test(txt)) {
          target.altitude_mode = 'low_altitude';
        } else if (!target.altitude_mode || target.altitude_mode === 'unknown') {
          const profile = trackMotionProfile(target.threat_type);
          if (profile.maxSpeedKmh > 1000) {
            target.altitude_mode = 'ballistic_arc';
          } else if (profile.maxSpeedKmh < 250) {
            target.altitude_mode = 'low_altitude';
          } else {
            target.altitude_mode = 'unknown';
          }
        }
      }

      // P4-A: Track Quality Index (TQI) — 0–100 composite quality score combining
      // observation density, source diversity, EKF health, and lifecycle state.
      {
        const obsCount = target.history.filter((h) => h.accepted).length;
        const obsDensity = Math.min(40, Math.log1p(obsCount) * 8);      // 0–40
        const sourceDiversity = Math.min(20, target.source_count * 5);   // 0–20
        const ekfHealth = target.ekf
          ? Math.max(0, 20 - (target.ekf.singularSkipCount * 4))         // 0–20
          : 10;
        const lifecycleBonus =
          target.lifecycle_state === 'CONFIRMED' ? 20 :
          target.lifecycle_state === 'TRACKING'  ? 12 :
          target.lifecycle_state === 'DETECTED'  ? 5  : 0;              // 0–20
        target.tqi = Math.round(Math.min(100, obsDensity + sourceDiversity + ekfHealth + lifecycleBonus));
      }

      // P5-E: Dynamic threat type reclassification — detect via text but only store
      // reclassified_from for admin display. Do NOT change threat_type at runtime:
      // it would corrupt the track profile (TTL, speed, EKF noise) mid-flight.
      if (target.last_message_text && !target.threat_type_reclassified_from) {
        const txt = target.last_message_text.toLowerCase();
        let inferredType: string | null = null;
        if (/балістич|iskander|іскандер|кн-23|кинджал|kinzhal/i.test(txt) && target.threat_type !== 'ballistic') {
          inferredType = 'ballistic';
        } else if (/fpv|фпв|дрон-камікадзе/i.test(txt) && target.threat_type !== 'fpv') {
          inferredType = 'fpv';
        } else if (/крилата|cruise|krylata|tomahawk/i.test(txt) && target.threat_type !== 'krylata') {
          inferredType = 'krylata';
        }
        // NOTE: intentionally NOT reclassifying shahed — too many false positives
        // (any message about shahed+kab combo would incorrectly reclassify the kab track).
        if (inferredType) {
          target.threat_type_reclassified_from = target.threat_type;
          // threat_type itself stays unchanged — only the diagnostic hint is set
        }
      }

      // P5-B: Negative evidence — track the score for admin display only.
      // Do NOT modify confidence here: "збито/знищено" appear constantly in Ukrainian
      // threat-channel messages (reporting on overall air defence results), not just for
      // the specific track being updated. False-positive rate is too high to use for
      // automatic confidence suppression — it would make tracks vanish prematurely.
      if (target.last_message_text) {
        const txt = target.last_message_text.toLowerCase();
        const negativeTerms = /знищен|збит|впало|впав|ліквідован|перехоплен|neutraliz|intercept|destroyed|shot.?down/i;
        if (negativeTerms.test(txt)) {
          target.negative_evidence_score = Math.min(1, (target.negative_evidence_score ?? 0) + 0.1);
        } else {
          target.negative_evidence_score = Math.max(0, (target.negative_evidence_score ?? 0) - 0.02);
        }
      }

      // P4-C: Apply exponential age decay to display_confidence
      if (typeof target.display_confidence === 'number') {
        const profile = trackMotionProfile(target.threat_type);
        const ageMs = Math.max(0, Date.now() - target.last_seen);
        const halfLife = profile.confidenceHalfLifeMs;
        const decayFactor = Math.pow(0.5, ageMs / halfLife);
        // Corroboration bonus: each additional source beyond 1 adds up to +5 points
        const corroborationBonus = Math.min(15, (target.source_count - 1) * 5);
        let dc = Math.min(100, target.display_confidence * decayFactor + corroborationBonus);

        // P4-E: EKF degradation penalty — when the filter keeps skipping updates
        // (singular S matrix), the position estimate is unreliable. Penalise confidence.
        if (target.ekf && target.ekf.singularSkipCount > 3) {
          dc *= 0.6;
        }

        target.display_confidence = Math.round(dc);
      }
    } catch (err) {
      // Never let rendering errors break the tracker — but log for debugging
      console.warn('[TRACKER_RENDERER] Error in _applyRendering:', target.id, err instanceof Error ? err.message : err);
    }
  }

  // ── P4-B: Swarm cluster assignment ─────────────────────────────────────────

  private assignSwarmCluster(target: TrackedTarget, nowMs = Date.now()): void {
    const CLUSTER_WINDOW_MS = 30 * 60_000;
    const CLUSTER_RADIUS_KM = 80;
    let bestClusterId: string | null = null;
    let bestClusterSize = 0;

    for (const other of this.targets.values()) {
      if (other.id === target.id) continue;
      if (other.threat_type !== target.threat_type) continue;
      if (!other.swarm_cluster_id) continue;
      const timeDiff = Math.abs(target.first_seen - other.first_seen);
      if (timeDiff > CLUSTER_WINDOW_MS) continue;
      const dist = haversineKm(target.lat, target.lng, other.lat, other.lng);
      if (dist > CLUSTER_RADIUS_KM) continue;

      // Count how many targets share this cluster_id
      const clusterSize = Array.from(this.targets.values()).filter(
        (t) => t.swarm_cluster_id === other.swarm_cluster_id,
      ).length;
      if (clusterSize > bestClusterSize) {
        bestClusterSize = clusterSize;
        bestClusterId = other.swarm_cluster_id!;
      }
    }

    if (bestClusterId) {
      target.swarm_cluster_id = bestClusterId;
    } else {
      // Check if there's any unassigned neighbor to form a new cluster with
      for (const other of this.targets.values()) {
        if (other.id === target.id || other.swarm_cluster_id) continue;
        if (other.threat_type !== target.threat_type) continue;
        const timeDiff = Math.abs(target.first_seen - other.first_seen);
        if (timeDiff > CLUSTER_WINDOW_MS) continue;
        const dist = haversineKm(target.lat, target.lng, other.lat, other.lng);
        if (dist > CLUSTER_RADIUS_KM) continue;
        // Found a neighbor — form a new cluster
        const newClusterId = `swarm_${target.threat_type}_${(target.first_seen / 1000).toFixed(0)}`;
        target.swarm_cluster_id = newClusterId;
        other.swarm_cluster_id = newClusterId;
        return;
      }
    }
  }

  // ── P3-D: Text-similarity deduplication ─────────────────────────────────────

  /**
   * Look at recent events in target.history and flag as repost-duplicates those
   * whose message text is ≥ 72% Jaccard-similar but came from different sources.
   * Returns the count of fingerprints suppressed.
   */
  deduplicateCrossChannelReposts(nowMs = Date.now()): number {
    const WINDOW_MS = 30 * 60_000;
    const SIMILARITY_THRESHOLD = 0.72;
    let suppressed = 0;

    for (const target of this.targets.values()) {
      const recent = target.history
        .filter((h) => h.accepted && nowMs - h.ts < WINDOW_MS)
        .slice(-20);
      for (let i = 0; i < recent.length; i++) {
        const hi = recent[i]!;
        if (!hi.message_text) continue;
        for (let j = i + 1; j < recent.length; j++) {
          const hj = recent[j]!;
          if (!hj.message_text) continue;
          if (hi.source === hj.source) continue;
          if (textShinglingSimilarity(hi.message_text, hj.message_text) >= SIMILARITY_THRESHOLD) {
            // Mark the later one as repost-suppressed in the replay index
            const laterFp = hi.ts >= hj.ts ? hi.fingerprint : hj.fingerprint;
            const item = this.fingerprintIndex.get(laterFp);
            if (item && !item.repostSuppressed) {
              this.fingerprintIndex.set(laterFp, { ...item, repostSuppressed: true });
              suppressed++;
            }
          }
        }
      }
    }
    return suppressed;
  }

  // ── P4-D: Track deduplication / merging ────────────────────────────────────

  detectAndMergeDuplicates(nowMs = Date.now()): number {
    const candidates = Array.from(this.targets.values()).filter((t) => {
      const lc = lifecycleAt(t, nowMs);
      return lc === 'TRACKING' || lc === 'CONFIRMED' || lc === 'DETECTED';
    });

    let merged = 0;
    for (let i = 0; i < candidates.length; i++) {
      for (let j = i + 1; j < candidates.length; j++) {
        const a = candidates[i]!;
        const b = candidates[j]!;
        if (norm(a.threat_type) !== norm(b.threat_type)) continue;
        if (!this.targets.has(a.id) || !this.targets.has(b.id)) continue;

        const distKm = haversineKm(a.lat, a.lng, b.lat, b.lng);
        if (distKm > 5) continue;

        const ageDiff = Math.abs(a.first_seen - b.first_seen);
        if (ageDiff > 10 * 60_000) continue;

        // Don't merge if they have different explicit upstream track IDs
        if (
          a.upstream_track_ids.length > 0 &&
          b.upstream_track_ids.length > 0 &&
          !a.upstream_track_ids.some((id) => b.upstream_track_ids.includes(id))
        ) continue;

        // Bearing check: moving in same direction (or no motion yet)
        const aBearing = a.movement_vector.bearing_deg;
        const bBearing = b.movement_vector.bearing_deg;
        if (aBearing != null && bBearing != null) {
          const bearingDiff = Math.abs(aBearing - bBearing) % 360;
          if (Math.min(bearingDiff, 360 - bearingDiff) > 40) continue;
        }

        // Merge lower-confidence into higher-confidence
        const [primary, secondary] = a.confidence >= b.confidence ? [a, b] : [b, a];

        // Transfer observations from secondary to primary
        for (const h of secondary.history) {
          if (!primary.event_fingerprints.includes(h.fingerprint)) {
            primary.history.push(h);
            primary.event_fingerprints.push(h.fingerprint);
            this.fingerprintIndex.set(h.fingerprint, { targetId: primary.id, seenAt: h.ts });
          }
        }
        for (const src of secondary.sources) {
          if (!primary.sources.includes(src)) primary.sources.push(src);
        }
        for (const uid of secondary.upstream_track_ids) {
          if (!primary.upstream_track_ids.includes(uid)) primary.upstream_track_ids.push(uid);
        }
        primary.source_count = primary.sources.length;
        // P1-C: confidence blending — merge, don't just max, so combined track reflects
        // the additive evidence of both observations. Cap at 0.99 to remain meaningful.
        const blendedConfidence = clamp01(
          primary.confidence + (1 - primary.confidence) * secondary.confidence * 0.4,
        );
        primary.confidence = Math.min(0.99, blendedConfidence);
        primary.first_seen = Math.min(primary.first_seen, secondary.first_seen);
        primary.count = Math.max(primary.count, secondary.count);

        // Remove secondary target
        this.targets.delete(secondary.id);
        this._applyRendering(primary);
        merged++;
      }
    }
    return merged;
  }

  // ── P3-C: Formation detection ────────────────────────────────────────────────

  /**
   * Detect tactical formations: groups of 3+ same-type targets that appeared within
   * FORMATION_WINDOW_MS of each other and are within FORMATION_RADIUS_KM.
   * Labels them with a shared `formation_id` on the target object.
   */
  detectFormations(nowMs = Date.now()): number {
    const FORMATION_WINDOW_MS = 20 * 60_000;
    const FORMATION_RADIUS_KM = 120;
    const MIN_FORMATION_SIZE = 3;

    const active = Array.from(this.targets.values()).filter((t) => {
      const lc = lifecycleAt(t, nowMs);
      return lc === 'TRACKING' || lc === 'CONFIRMED' || lc === 'DETECTED';
    });

    // Group by threat_type and temporal proximity
    const byType = new Map<string, TrackedTarget[]>();
    for (const t of active) {
      const k = t.threat_type;
      if (!byType.has(k)) byType.set(k, []);
      byType.get(k)!.push(t);
    }

    let formationsDetected = 0;
    for (const [, group] of byType) {
      // Simple O(n²) clustering: if a target is within radius + window of a cluster, add it
      const clusters: TrackedTarget[][] = [];
      for (const t of group) {
        let added = false;
        for (const cluster of clusters) {
          const seed = cluster[0]!;
          const timeDiff = Math.abs(t.first_seen - seed.first_seen);
          if (timeDiff > FORMATION_WINDOW_MS) continue;
          const dist = haversineKm(t.lat, t.lng, seed.lat, seed.lng);
          if (dist <= FORMATION_RADIUS_KM) {
            cluster.push(t);
            added = true;
            break;
          }
        }
        if (!added) clusters.push([t]);
      }
      for (const cluster of clusters) {
        if (cluster.length < MIN_FORMATION_SIZE) {
          // Clear formation_id for small clusters
          for (const t of cluster) t.formation_id = undefined;
          continue;
        }
        const seed = cluster[0]!;
        const fid = seed.formation_id || `formation_${seed.threat_type}_${(seed.first_seen / 1000).toFixed(0)}`;
        for (const t of cluster) t.formation_id = fid;
        formationsDetected++;
      }
    }
    return formationsDetected;
  }

  /**
   * Detect tight swarms: groups of 2+ targets that are very close (< 5km) and have the same vector.
   * Labels them with a shared `swarm_cluster_id` on the target object.
   */
  detectSwarms(nowMs = Date.now()): number {
    const SWARM_RADIUS_KM = 5;
    const BEARING_TOLERANCE = 20;

    const active = Array.from(this.targets.values()).filter((t) => {
      const lc = lifecycleAt(t, nowMs);
      return lc === 'TRACKING' || lc === 'CONFIRMED' || lc === 'DETECTED';
    });

    const byType = new Map<string, TrackedTarget[]>();
    for (const t of active) {
      const k = t.threat_type;
      if (!byType.has(k)) byType.set(k, []);
      byType.get(k)!.push(t);
    }

    let swarmsDetected = 0;
    for (const [, group] of byType) {
      const clusters: TrackedTarget[][] = [];
      for (const t of group) {
        let added = false;
        for (const cluster of clusters) {
          const seed = cluster[0]!;
          const dist = haversineKm(t.lat, t.lng, seed.lat, seed.lng);
          if (dist > SWARM_RADIUS_KM) continue;
          
          if (t.movement_vector.bearing_deg != null && seed.movement_vector.bearing_deg != null) {
            let diff = Math.abs(t.movement_vector.bearing_deg - seed.movement_vector.bearing_deg);
            if (diff > 180) diff = 360 - diff;
            if (diff <= BEARING_TOLERANCE) {
              cluster.push(t);
              added = true;
              break;
            }
          } else if (dist <= 2) {
             // If no bearing, group if extremely close
             cluster.push(t);
             added = true;
             break;
          }
        }
        if (!added) clusters.push([t]);
      }
      for (const cluster of clusters) {
        if (cluster.length < 2) {
          for (const t of cluster) t.swarm_cluster_id = undefined;
          continue;
        }
        const seed = cluster[0]!;
        const sid = seed.swarm_cluster_id || `swarm_${seed.threat_type}_${seed.id.substring(0,6)}`;
        for (const t of cluster) t.swarm_cluster_id = sid;
        swarmsDetected++;
      }
    }
    return swarmsDetected;
  }

  // ── P1-E: Raion/oblast geo-context enrichment ───────────────────────────────

  /**
   * Enrich targets with a resolved GADM oblast HASC code based on their current
   * lat/lng. Simple bounding-box table keyed by oblast. Returns count updated.
   */
  enrichGeoContext(): number {
    let updated = 0;
    for (const target of this.targets.values()) {
      const hasc = resolveOblastHasc(target.lat, target.lng);
      if (hasc && hasc !== (target as Record<string, unknown>)['tracker_oblast_hasc']) {
        (target as Record<string, unknown>)['tracker_oblast_hasc'] = hasc;
        updated++;
      }
    }
    return updated;
  }

  // ── P2-E: Predicted impact zone ─────────────────────────────────────────────

  /**
   * Compute the 1-σ impact zone radius in km for a tracked target's predicted endpoint.
   * Uses the EKF covariance matrix + bearing uncertainty + time-to-target.
   */
  computeImpactZone(target: TrackedTarget, nowMs = Date.now()): number | null {
    if (!target.ekf) return null;
    const sigmaKm = target.ekf.positionSigmaKm();
    if (!Number.isFinite(sigmaKm)) return null;

    const profile = trackMotionProfile(target.threat_type);
    const etaSec = typeof target.eta_seconds === 'number' ? target.eta_seconds : null;
    const speedKmh = target.speed_estimate_kmh ?? profile.nominalSpeedKmh;
    const speedKms = speedKmh / 3600;

    // ETA uncertainty contribution: ±5% of remaining travel distance
    const remainingKm = etaSec != null ? speedKms * etaSec : speedKmh * 0.1;
    const etaUncertaintyKm = remainingKm * 0.05;

    // Position sigma grows with time-to-target (process noise integration)
    const dtSec = Math.max(0, (nowMs - target.last_seen) / 1000);
    const driftKm = Math.sqrt(target.ekf.qProcessNoise) * dtSec * 111.32;

    return Math.round(Math.min(50, sigmaKm * 3 + etaUncertaintyKm + driftKm) * 10) / 10;
  }

  // ── P3-A: Swarm flock centroid tracker ─────────────────────────────────────

  /**
   * For each swarm cluster, compute the geometric centroid and attach it to each
   * member target as `swarm_centroid`.  Returns the number of clusters updated.
   */
  computeSwarmCentroids(nowMs = Date.now()): number {
    const clusterMap = new Map<string, TrackedTarget[]>();
    for (const t of this.targets.values()) {
      if (!t.swarm_cluster_id) continue;
      const lc = lifecycleAt(t, nowMs);
      if (lc === 'LOST' || lc === 'DESTROYED' || lc === 'REJECTED') continue;
      if (!clusterMap.has(t.swarm_cluster_id)) clusterMap.set(t.swarm_cluster_id, []);
      clusterMap.get(t.swarm_cluster_id)!.push(t);
    }
    let updated = 0;
    for (const [, members] of clusterMap) {
      if (members.length < 2) continue;
      const lat = members.reduce((s, m) => s + m.lat, 0) / members.length;
      const lng = members.reduce((s, m) => s + m.lng, 0) / members.length;
      const centroid = { lat, lng, size: members.length };
      for (const m of members) m.swarm_centroid = centroid;
      updated++;
    }
    return updated;
  }

  // ── P3-B: Cross-alert oblast correlation ───────────────────────────────────

  /**
   * Compute a cross-oblast correlation score for each active target.  When 3+
   * targets of the same threat type appear across different oblasts within
   * CORR_WINDOW_MS, each gets a boosted `cross_oblast_score` (0..1).
   */
  computeCrossOblastCorrelation(nowMs = Date.now()): void {
    const CORR_WINDOW_MS = 15 * 60_000;
    const byType = new Map<string, { target: TrackedTarget; oblast: string }[]>();

    for (const t of this.targets.values()) {
      const lc = lifecycleAt(t, nowMs);
      if (lc === 'LOST' || lc === 'DESTROYED' || lc === 'REJECTED') continue;
      if (nowMs - t.last_seen > CORR_WINDOW_MS) continue;
      const oblast = (t as Record<string, unknown>)['tracker_oblast_hasc'] as string | undefined;
      if (!oblast) continue;
      const key = t.threat_type;
      if (!byType.has(key)) byType.set(key, []);
      byType.get(key)!.push({ target: t, oblast });
    }

    for (const [, entries] of byType) {
      const oblasts = new Set(entries.map((e) => e.oblast));
      const score = Math.min(1, (oblasts.size - 1) / 4); // 0 for 1 oblast, 1 for 5+ oblasts
      for (const e of entries) {
        e.target.cross_oblast_score = Math.round(score * 100) / 100;
      }
    }
  }

  // ── P3-E: Ghost pool cooperative handoff ────────────────────────────────────

  /**
   * Move recently-LOST targets to the ghost pool for a short grace period.
   * If a new event comes in that closely matches a ghost, hand off (re-activate)
   * rather than creating a brand-new track.
   */
  updateGhostPool(nowMs = Date.now()): void {
    const GHOST_TTL_MS = 8 * 60_000;
    // Add newly-lost targets to the ghost pool
    for (const t of this.targets.values()) {
      const lc = lifecycleAt(t, nowMs);
      if (lc === 'LOST' && !this.ghostPool.has(t.id)) {
        this.ghostPool.set(t.id, { target: t, expireAt: nowMs + GHOST_TTL_MS });
      }
    }
    // Expire stale ghosts
    for (const [id, ghost] of this.ghostPool) {
      if (nowMs > ghost.expireAt) this.ghostPool.delete(id);
    }
  }

  private tryGhostPoolHandoff(event: CandidateEvent, nowMs = Date.now()): TrackedTarget | null {
    const HANDOFF_RADIUS_KM = 25;
    let best: { id: string; target: TrackedTarget; distKm: number } | null = null;
    for (const [id, ghost] of this.ghostPool) {
      if (norm(ghost.target.threat_type) !== norm(event.threat_type)) continue;
      const dist = haversineKm(ghost.target.lat, ghost.target.lng, event.lat, event.lng);
      if (dist > HANDOFF_RADIUS_KM) continue;
      if (!best || dist < best.distKm) best = { id, target: ghost.target, distKm: dist };
    }
    if (!best) return null;
    const t = best.target;
    this.ghostPool.delete(best.id);
    // Re-activate the target
    t.lifecycle_state = 'TRACKING';
    t.ghost_pool_origin = best.id;
    this.targets.set(t.id, t);
    return t;
  }

  // ── P4-B: Automatic stale track reaper ─────────────────────────────────────

  /**
   * Remove targets that have been LOST or STALE for longer than their profile's
   * `lostMs` threshold, freeing memory and reducing noise in queries.
   * Returns count of reaped tracks.
   */
  reapStaleTracks(nowMs = Date.now()): number {
    let reaped = 0;
    for (const [id, target] of this.targets.entries()) {
      const profile = trackMotionProfile(target.threat_type);
      const lc = lifecycleAt(target, nowMs);
      if (lc === 'DESTROYED' || lc === 'REJECTED') {
        this.targets.delete(id);
        reaped++;
        continue;
      }
      
      // P6-F: MHT Branch Pruning
      if (target.mht_parent_id) {
        const parent = this.targets.get(target.mht_parent_id);
        if (parent) {
          // Prune branches that fell behind in updates compared to their parent
          if (nowMs - target.last_seen > 120_000 && parent.last_seen > target.last_seen) {
            this.targets.delete(id);
            reaped++;
            continue;
          }
          // Or if parent fell behind branch
          if (nowMs - parent.last_seen > 120_000 && target.last_seen > parent.last_seen) {
            this.targets.delete(parent.id);
            reaped++;
            // Don't continue, we just deleted the parent, not this target
          }
        }
      }

      if (lc === 'LOST' || lc === 'STALE') {
        const ageMs = nowMs - target.last_seen;
        if (ageMs > profile.lostMs * 2) {
          this.targets.delete(id);
          reaped++;
        }
      }
    }
    return reaped;
  }

  // ── P5-C: Launch origin inference via backward projection ───────────────────

  /**
   * For targets with enough track history, back-project their trajectory to estimate
   * the launch/origin point.  Writes `origin_inference` onto the target.
   * Returns count of targets updated.
   */
  inferLaunchOrigins(nowMs = Date.now()): number {
    let updated = 0;
    for (const t of this.targets.values()) {
      const acceptedObs = t.history.filter((h) => h.accepted).length;
      if (acceptedObs < 3) continue;
      if (t.movement_vector.bearing_deg == null) continue;
      const speedKmh = t.speed_estimate_kmh ?? trackMotionProfile(t.threat_type).nominalSpeedKmh;
      if (speedKmh < 10) continue;

      // Use earliest and latest accepted observations to establish a track vector
      const sorted = [...t.history.filter((h) => h.accepted)].sort((a, b) => a.ts - b.ts);
      const first = sorted[0]!;
      const last = sorted[sorted.length - 1]!;
      const dtHrs = (last.ts - first.ts) / 3_600_000;
      if (dtHrs < 0.01) continue;

      // Backward projection: extend the vector by dtHrs from the first observation
      const reverseBearing = (t.movement_vector.bearing_deg + 180) % 360;
      const travelKm = speedKmh * dtHrs;
      const destRad = travelKm / 6371;
      const lat1 = (first.lat * Math.PI) / 180;
      const lng1 = (first.lng * Math.PI) / 180;
      const brRad = (reverseBearing * Math.PI) / 180;
      const lat2 = Math.asin(
        Math.sin(lat1) * Math.cos(destRad) + Math.cos(lat1) * Math.sin(destRad) * Math.cos(brRad),
      );
      const lng2 = lng1 + Math.atan2(
        Math.sin(brRad) * Math.sin(destRad) * Math.cos(lat1),
        Math.cos(destRad) - Math.sin(lat1) * Math.sin(lat2),
      );
      const inferredLat = (lat2 * 180) / Math.PI;
      const inferredLng = (lng2 * 180) / Math.PI;

      const obsConfidence = Math.min(0.9, 0.3 + acceptedObs * 0.1);
      const siteMatch = intersectLaunchSite(inferredLat, inferredLng, t.threat_type);

      t.origin_inference = {
        lat: Math.round(inferredLat * 1000) / 1000,
        lng: Math.round(inferredLng * 1000) / 1000,
        confidence: Math.round(obsConfidence * 100) / 100,
        method: siteMatch ? `launch_site:${siteMatch.name}` : 'backward_projection',
      };
      updated++;
    }
    return updated;
  }

  // ── P5-D: Worker→tracker trajectory feedback ────────────────────────────────

  /**
   * Accept accuracy feedback from the worker (e.g., when an impact is confirmed and
   * the actual landing point is known).  This updates the channel's geo bias table
   * and stores the error on the target for dashboards.
   */
  recordTrajectoryFeedback(
    targetId: string,
    actualLat: number,
    actualLng: number,
    nowMs = Date.now(),
  ): boolean {
    const target = this.targets.get(targetId);
    if (!target) return false;
    const predictedLat = target.tracker_target?.[0] ?? target.lat;
    const predictedLng = target.tracker_target?.[1] ?? target.lng;
    const errorKm = haversineKm(predictedLat, predictedLng, actualLat, actualLng);
    target.trajectory_feedback = { error_km: Math.round(errorKm * 10) / 10, reported_at: nowMs };

    // Feed systematic error back into channel geo bias table
    const source = target.sources[0];
    if (source && errorKm < 100) {
      const dlat = actualLat - predictedLat;
      const dlng = actualLng - predictedLng;
      const existing = CHANNEL_GEO_BIAS[source.toLowerCase()];
      if (existing) {
        // EMA correction — blend new error into existing bias
        CHANNEL_GEO_BIAS[source.toLowerCase()] = {
          dlat: existing.dlat * 0.8 + dlat * 0.2,
          dlng: existing.dlng * 0.8 + dlng * 0.2,
        };
      } else {
        CHANNEL_GEO_BIAS[source.toLowerCase()] = { dlat: dlat * 0.2, dlng: dlng * 0.2 };
      }
    }
    return true;
  }

  // ── P3-C: Split angle analysis ──────────────────────────────────────────────

  /**
   * Compute the angle between the parent track's bearing and the split track's
   * initial bearing.  A shallow angle (< 45°) indicates a lane separation;
   * a deep angle (> 90°) suggests a genuine turn or new threat.
   */
  private computeSplitAngle(parent: TrackedTarget, splitLat: number, splitLng: number): number | null {
    if (parent.movement_vector.bearing_deg == null) return null;
    const splitBearing = bearingBetween(parent.lat, parent.lng, splitLat, splitLng);
    if (splitBearing == null) return null;
    return angularDiffDeg(parent.movement_vector.bearing_deg, splitBearing);
  }

  /** Override createSplitTarget to annotate split_shallow_angle. */
  private createSplitTarget(
    parent: TrackedTarget,
    event: CandidateEvent,
    fp: string,
    confidence: number,
    publication: MarkerPublicationDecision,
  ): TrackedTarget {
    const target = this.createTarget(event, fp, confidence, publication);
    target.parent_track_id = parent.id;
    
    // P6-D: Swarm Split Inheritance — child inherits parent's covariance and velocity
    if (parent.ekf && target.ekf) {
      if (parent.ekf instanceof IMMFilter2D && target.ekf instanceof IMMFilter2D) {
        target.ekf = IMMFilter2D.fromJSON(parent.ekf.toJSON());
        target.ekf.resetPosition(event.lat, event.lng);
      } else if (parent.ekf instanceof KalmanFilter2D && target.ekf instanceof KalmanFilter2D) {
        target.ekf = KalmanFilter2D.fromJSON(parent.ekf.toJSON());
        target.ekf.resetPosition(event.lat, event.lng);
      }
    }

    const splitAngle = this.computeSplitAngle(parent, event.lat, event.lng);
    if (splitAngle !== null) {
      target.split_shallow_angle = splitAngle < 45;
    }
    this.appendHistory(target, event, fp, true, 'split_from_parent', confidence);
    return target;
  }

  // ── P5-A: Predictive alarm pre-notification ─────────────────────────────────

  /**
   * Scan all active targets and return those expected to cross a region of interest
   * within `horizonSec` seconds based on current trajectory.  Used by the alarm
   * engine to pre-notify before a threat actually enters an oblast.
   */
  getPredictiveAlarms(
    regions: Array<{ id: string; lat: number; lng: number; radiusKm: number }>,
    horizonSec: number = 300,
    nowMs = Date.now(),
  ): Array<{ targetId: string; regionId: string; etaSec: number; confidence: number }> {
    const alarms: Array<{ targetId: string; regionId: string; etaSec: number; confidence: number }> = [];

    for (const t of this.targets.values()) {
      const lc = lifecycleAt(t, nowMs);
      if (lc === 'LOST' || lc === 'DESTROYED' || lc === 'REJECTED') continue;
      const bearing = t.movement_vector.bearing_deg;
      const speed = t.speed_estimate_kmh ?? trackMotionProfile(t.threat_type).nominalSpeedKmh;
      if (bearing == null || speed < 5) continue;

      for (const region of regions) {
        // Project forward in steps of 30 sec and check proximity to region center
        for (let stepSec = 30; stepSec <= horizonSec; stepSec += 30) {
          const travelKm = (speed / 3600) * stepSec;
          const projected = destinationPoint(t.lat, t.lng, bearing, travelKm);
          const distKm = haversineKm(projected[0], projected[1], region.lat, region.lng);
          if (distKm <= region.radiusKm) {
            alarms.push({
              targetId: t.id,
              regionId: region.id,
              etaSec: stepSec,
              confidence: t.confidence * (1 - distKm / region.radiusKm),
            });
            break; // Only the first crossing per region per target
          }
        }
      }
    }
    return alarms;
  }

  // ── P3-D: Time-of-flight range gate (public wrapper) ────────────────────────

  /**
   * Check whether an event passes the range gate relative to a tracked target.
   * Returns false when the implied speed would violate the threat profile by > 15%.
   */
  checkTofGate(event: CandidateEvent, target: TrackedTarget): boolean {
    const dtMs = event.ts - target.first_seen;
    if (dtMs <= 0) return true;
    return mislRangeGate(event, target, dtMs);
  }

  // ── P1-A: Multi-head association voting ─────────────────────────────────────

  /**
   * Vote across multiple association hypotheses.  Returns the top-K candidates
   * sorted by a weighted consensus score that combines distance, bearing, and
   * observation density.  The primary `findAssociation` pick is usually #1, but
   * for ambiguous events callers can inspect alternatives.
   */
  findAssociationCandidates(
    event: CandidateEvent,
    topK: number = 3,
  ): Array<{ target: TrackedTarget; score: number; breakdown: TargetAssociationBreakdown }> {
    const candidates: Array<{ target: TrackedTarget; score: number; breakdown: TargetAssociationBreakdown }> = [];
    const eventCount = normalizeCount(event.count);
    const quality = observationQuality(event);
    const textIntent = inferTextIntent(event);

    for (const target of this.targets.values()) {
      if (norm(target.threat_type) !== norm(event.threat_type)) continue;
      const lc = lifecycleAt(target, event.ts);
      if (lc === 'LOST' || lc === 'DESTROYED' || lc === 'REJECTED') continue;
      
      const sameUpstreamTrack = hasSameUpstreamTrack(target, event);
      if (hasDifferentExplicitGroup(target, event)) continue;
      
      if (
        !sameUpstreamTrack &&
        target.count > 1 &&
        eventCount < target.count &&
        target.count - eventCount >= 2 &&
        eventCount <= Math.ceil(target.count * 0.7)
      ) {
        continue;
      }

      const sameRegion = Boolean(target.region && event.region && norm(target.region) === norm(event.region));
      if (
        target.region &&
        event.region &&
        !sameRegion &&
        !sameUpstreamTrack
      ) continue;

      let radiusKm = maxAssociationRadius(event, this.options, target);
      if (sameUpstreamTrack) {
        const profile = trackMotionProfile(event.threat_type);
        const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 0);
        const trackIdMotionBudgetKm = Math.max(25, profile.nominalSpeedKmh * dtHours * 1.65);
        radiusKm = Math.min(90, Math.max(radiusKm, trackIdMotionBudgetKm));
      }
      // P4-A: EKF sigma gate — tighten radius when filter is confident
      if (target.ekf) {
        const sigmaKm = target.ekf.positionSigmaKm();
        const ekfGateKm = Math.max(5, sigmaKm * 3);
        radiusKm = Math.min(radiusKm, Math.max(5, ekfGateKm));
      }

      const predicted = projectedTargetPosition(target, event.ts);
      const pointDist = haversineKm(predicted.lat, predicted.lng, event.lat, event.lng);
      const corridorDist = predicted.projected
        ? segmentDistanceKm(target.lat, target.lng, predicted.lat, predicted.lng, event.lat, event.lng)
        : pointDist;
      const dist = Math.min(pointDist, corridorDist);
      if (dist > radiusKm) continue;

      const samePlace = target.place && event.place && norm(target.place) === norm(event.place);
      const countPenalty = target.count !== eventCount ? Math.min(18, Math.abs(target.count - eventCount) * 6) : 0;
      const bearingPenalty = courseTurnPenalty(target, event);
      const corridorPenalty = courseCorridorPenalty(target, event);
      const innovationPenalty = movementInnovationPenalty(target, event, dist);
      const qualityPenalty = qualityAssociationPenalty(quality, sameUpstreamTrack, !!samePlace);
      const groupBonus = groupAssociationBonus(textIntent, target, event);
      const acceptedObs = target.history.filter((h) => h.accepted).length;
      const densityBonus = Math.min(12, Math.log1p(acceptedObs) * 2.5);

      const score = 100
        - (dist / radiusKm) * 65
        + (samePlace ? 12 : 0)
        + (sameUpstreamTrack ? 25 : 0)
        + densityBonus
        + groupBonus
        - countPenalty
        - bearingPenalty
        - corridorPenalty
        - innovationPenalty
        - qualityPenalty;

      const threshold = associationScoreThreshold(target, event, !!samePlace);
      const breakdown: TargetAssociationBreakdown = {
        score: roundScore(score),
        threshold,
        distance_km: round1(dist),
        radius_km: round1(radiusKm),
        same_place: !!samePlace,
        same_upstream_track: sameUpstreamTrack,
        count_penalty: roundScore(countPenalty),
        bearing_penalty: roundScore(bearingPenalty),
        corridor_penalty: roundScore(corridorPenalty),
        innovation_penalty: roundScore(innovationPenalty),
        quality_penalty: roundScore(qualityPenalty),
        group_bonus: roundScore(groupBonus),
        text_intent: textIntent,
        observation_quality: quality,
        accepted: score >= threshold,
        reason: score >= threshold ? 'associated' : 'score_below_threshold',
      };
      candidates.push({ target, score, breakdown });
    }

    return candidates.sort((a, b) => b.score - a.score).slice(0, topK);
  }

  getTargetById(id: string): TrackedTarget | undefined {
    return this.targets.get(id);
  }

  getAllTargets(): Map<string, TrackedTarget> {
    return this.targets;
  }

  getGhostPool(): Map<string, { target: TrackedTarget; expireAt: number }> {
    return this.ghostPool;
  }
}

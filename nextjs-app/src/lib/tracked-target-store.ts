import { loadSettings } from '@/lib/admin/data';
import { clearMarkerDerivedApiCachesLocal, invalidateMarkerDerivedCaches } from '@/lib/cache';
import { getRawMessages } from '@/lib/markers-store';
import { getRedis, isRedisDisabledInThisProcess, redisGet, redisIncr, redisSet } from '@/lib/redis';
import {
  TargetTrackerEngine,
  type CandidateEvent,
  type TrackedTarget,
  type TrackerDecision,
} from '@/lib/target-tracker-engine';
import { KalmanFilter2D } from '@/lib/ekf';
import { sanitizeTrackedTarget } from '@/lib/target-serialization';
import { estimateTrackState } from '@/lib/track-estimator';
import { trackMotionProfile } from '@/lib/track-motion-profile';
import { broadcastSSE } from '@/lib/chat-sse-stream';

export { sanitizeTrackedTarget };

const REDIS_TARGETS_KEY = 'targets:tracked:v1';
const REDIS_TARGETS_VERSION_KEY = 'targets:tracked:version';
const REDIS_TARGETS_TTL_SECONDS = 6 * 60 * 60;
// P4-C: Smart TTL — extend Redis TTL when there are many active tracks to prevent data loss
// during high-traffic events. Max 24h, min 6h.
const REDIS_TARGETS_MAX_TTL_SECONDS = 24 * 60 * 60;

type TargetStoreState = {
  initialized: boolean;
  initPromise: Promise<void> | null;
  engine: TargetTrackerEngine | null;
  lastVersion: number;
  writeLock: Promise<void>;
};

const GLOBAL_KEY = '__neptun_tracked_target_store__';

function getState(): TargetStoreState {
  if (!(globalThis as Record<string, unknown>)[GLOBAL_KEY]) {
    (globalThis as Record<string, unknown>)[GLOBAL_KEY] = {
      initialized: false,
      initPromise: null,
      engine: null,
      lastVersion: 0,
      writeLock: Promise.resolve(),
    } as TargetStoreState;
  }
  return (globalThis as Record<string, unknown>)[GLOBAL_KEY] as TargetStoreState;
}

function withTargetWriteLock<T>(fn: () => Promise<T>): Promise<T> {
  const state = getState();
  const prev = state.writeLock;
  let resolve!: () => void;
  state.writeLock = new Promise<void>((r) => { resolve = r; });
  return prev.then(fn).finally(() => resolve());
}

function epochMs(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    return value > 10_000_000_000 ? Math.round(value) : Math.round(value * 1000);
  }
  if (typeof value === 'string' && value.trim()) {
    const t = new Date(value.includes('T') ? value : value.replace(' ', 'T')).getTime();
    if (Number.isFinite(t) && t > 0) return t;
  }
  return Date.now();
}

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

function norm(value: unknown): string {
  return String(value || '').normalize('NFKC').trim().toLowerCase();
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim() !== '');
}


function markerToCandidateEvent(marker: Record<string, unknown>): CandidateEvent | null {
  const lat = numberOrUndefined(marker.lat);
  const lng = numberOrUndefined(marker.lng);
  if (lat == null || lng == null) return null;

  return {
    event_id: String(marker.msg_id || marker.message_id || marker.id || ''),
    fingerprint: typeof marker.event_fingerprint === 'string' ? marker.event_fingerprint : undefined,
    upstream_track_id: typeof marker.track_id === 'string' ? marker.track_id : undefined,
    ts: epochMs(marker.created_at_epoch || marker.last_update_epoch || marker.ts || marker.date || marker.timestamp),
    lat,
    lng,
    threat_type: String(marker.threat_type || marker.type || 'unknown'),
    count: countOrOne(marker.count),
    region: typeof marker.region === 'string' ? marker.region : typeof marker.oblast === 'string' ? marker.oblast : undefined,
    place: typeof marker.place === 'string'
      ? marker.place
      : typeof marker.city === 'string'
        ? marker.city
        : typeof marker.location === 'string'
          ? marker.location
          : undefined,
    source: typeof marker.channel_name === 'string'
      ? marker.channel_name
      : typeof marker.channel === 'string'
        ? marker.channel
        : undefined,
    channel_priority: numberOrUndefined(marker.channel_priority),
    confidence: numberOrUndefined(marker.confidence),
    locality_confidence: numberOrUndefined(marker.locality_confidence),
    bearing_deg: numberOrUndefined(marker.course_bearing) ?? numberOrUndefined(marker.ticker_bearing) ?? null,
    manual: Boolean(marker.manual),
    raw: marker,
  };
}

function targetToStoreRecord(target: TrackedTarget, nowMs = Date.now()): Record<string, unknown> {
  const history = Array.isArray(target.history) ? target.history : [];
  const accepted = history.filter((h) => h.accepted);
  const rejected = history.filter((h) => !h.accepted);
  const latest = accepted[accepted.length - 1] ?? target.history[target.history.length - 1];
  const priorityValues = accepted
    .map((h) => h.channel_priority)
    .filter((p): p is number => typeof p === 'number' && Number.isFinite(p));
  const bestChannelPriority = priorityValues.length > 0 ? Math.min(...priorityValues) : undefined;
  const observations = accepted.map((h) => ({
    lat: h.lat,
    lng: h.lng,
    ts: h.ts,
    source: h.source,
    channel_priority: h.channel_priority,
    count: h.count,
  }));
  const baseRecord: Record<string, unknown> = {
    lat: target.lat,
    lng: target.lng,
    threat_type: target.threat_type,
    confidence: target.confidence,
    count: target.count,
    observations,
    speed_kmh: target.speed_estimate_kmh ?? undefined,
    computed_speed_kmh: target.speed_estimate_kmh ?? undefined,
    course_bearing: target.movement_vector.bearing_deg,
    ticker_bearing: target.movement_vector.bearing_deg,
    created_at_epoch: target.first_seen,
    last_update_epoch: target.last_seen,
  };
  const estimate = estimateTrackState(baseRecord, nowMs);

  // P1-C: For EKF-tracked targets use the engine's own projected position rather than
  // the estimateTrackState 0.35× visual multiplier, which diverges from engine physics.
  let lat: number;
  let lng: number;
  if (target.ekf && estimate.state !== 'lost') {
    const profile = trackMotionProfile(target.threat_type);
    const ageMs = Math.max(0, nowMs - target.last_seen);
    if (ageMs < profile.extrapolateMs) {
      const ekfPred = target.ekf.predictedPosition(ageMs / 1000);
      lat = ekfPred.lat;
      lng = ekfPred.lng;
    } else {
      lat = target.lat;
      lng = target.lng;
    }
  } else {
    lat = estimate.state === 'lost' ? target.lat : estimate.lat;
    lng = estimate.state === 'lost' ? target.lng : estimate.lng;
  }

  const trackState = target.lifecycle_state === 'LOST'
    ? 'lost'
    : target.lifecycle_state === 'STALE'
      ? 'stale'
      : estimate.state;
  const visualConfidence = Math.round(estimate.visualConfidence * 100) / 100;

  return {
    id: target.id,
    track_id: target.id,
    lat,
    lng,
    threat_type: target.threat_type,
    type: target.threat_type,
    count: target.count,
    place: target.place || '',
    region: target.region || '',
    text: latest ? `tracked:${target.threat_type}:${target.place || target.region || target.id}` : '',
    date: new Date(target.last_seen).toISOString(),
    ts: target.last_seen,
    created_at_epoch: target.first_seen,
    last_update_epoch: target.last_seen,
    confidence: visualConfidence,
    target_confidence: Math.round(target.confidence * 100) / 100,
    target_lifecycle_state: target.lifecycle_state,
    source_count: target.source_count,
    upstream_track_ids: target.upstream_track_ids,
    observations,
    positions: observations,
    rejected_observations: rejected.map((h) => ({
      lat: h.lat,
      lng: h.lng,
      ts: h.ts,
      source: h.source,
      reason: h.reason,
      confidence: h.confidence,
      count: h.count,
    })),
    observation_count: accepted.length,
    speed_kmh: estimate.speedKmh || target.speed_estimate_kmh || undefined,
    computed_speed_kmh: estimate.speedKmh || target.speed_estimate_kmh || undefined,
    course_bearing: estimate.bearingDeg,
    ticker_bearing: estimate.bearingDeg,
    track_state: trackState,
    track_confidence: visualConfidence,
    motion_reason: estimate.reason,
    age_ms: estimate.ageMs,
    is_estimated: estimate.isEstimated,
    channel_priority: bestChannelPriority,
    // P1-A: Be honest about position quality for tracked targets.
    // - placement_mode: 'tracked' when EKF is active (point-level but fused), else use raw event mode.
    // - resolve_status: use the raw event's status (honest); publication filters handle it correctly.
    // - position_source: new field for diagnostic consumers.
    placement_mode: target.ekf ? 'tracked' : (target.last_placement_mode || 'point'),
    resolve_status: target.last_resolve_status || 'ok',
    geocode_tier: target.ekf ? 'tracked' : (target.last_placement_mode === 'point' ? 'point' : 'area'),
    position_source: target.ekf ? 'ekf' : 'raw',
    event_fingerprint: target.event_fingerprints[target.event_fingerprints.length - 1],
    publication_class: target.publication?.classification,
    publication_score: target.publication?.score,
    publication_reasons: target.publication?.reasons,
    manual: !!target.manual,
    last_observation: target.last_observation,
    predicted_position: target.predicted_position,
    last_measurement: target.last_measurement,
    last_association: target.last_association,
    association_score: target.last_association?.score,
    association_reason: target.last_association?.reason,
    is_loitering: target.is_loitering === true ? true : undefined,
    heading_confidence: target.heading_confidence,
    position_estimated: target.position_estimated === true ? true : undefined,
    eta_seconds: typeof target.eta_seconds === 'number' ? target.eta_seconds : undefined,
    display_confidence: typeof target.display_confidence === 'number' ? target.display_confidence : undefined,
    rendered_lat: typeof target.rendered_lat === 'number' ? target.rendered_lat : undefined,
    rendered_lng: typeof target.rendered_lng === 'number' ? target.rendered_lng : undefined,
    last_message_text: target.last_message_text,
    last_resolve_status: target.last_resolve_status,
    last_placement_mode: target.last_placement_mode,
    parent_track_id: target.parent_track_id,
    swarm_cluster_id: target.swarm_cluster_id,
    ekf: target.ekf?.toJSON(),
    // P3-A: pass renderer trail/target through to map layer
    tracker_trail: target.tracker_trail,
    tracker_target: target.tracker_target,
    // New fields from tracker-plan-v3
    tqi: typeof target.tqi === 'number' ? target.tqi : undefined,
    altitude_mode: target.altitude_mode,
    coastal_transition: target.coastal_transition === true ? true : undefined,
    trajectory_confidence: typeof target.trajectory_confidence === 'number' ? target.trajectory_confidence : undefined,
    formation_id: target.formation_id,
    publication_history: target.publication_history?.length ? target.publication_history : undefined,
    tracker_oblast_hasc: (target as Record<string, unknown>)['tracker_oblast_hasc'] as string | undefined,
    // New fields from tracker-plan-v4
    burst_score: typeof target.burst_score === 'number' ? target.burst_score : undefined,
    maneuver_detected: target.maneuver_detected === true ? true : undefined,
    eta_p10: typeof target.eta_p10 === 'number' ? target.eta_p10 : undefined,
    eta_p90: typeof target.eta_p90 === 'number' ? target.eta_p90 : undefined,
    swarm_centroid: target.swarm_centroid,
    cross_oblast_score: typeof target.cross_oblast_score === 'number' ? target.cross_oblast_score : undefined,
    split_shallow_angle: typeof target.split_shallow_angle === 'boolean' ? target.split_shallow_angle : undefined,
    ghost_pool_origin: target.ghost_pool_origin,
    negative_evidence_score: typeof target.negative_evidence_score === 'number' ? target.negative_evidence_score : undefined,
    origin_inference: target.origin_inference,
    trajectory_feedback: target.trajectory_feedback,
    threat_type_history: target.threat_type_history?.length ? target.threat_type_history : undefined,
    threat_type_reclassified_from: target.threat_type_reclassified_from,
  };
}

async function persistTargets(): Promise<void> {
  const state = getState();
  const snapshot = state.engine?.snapshot() ?? [];
  // P4-C: Smart TTL — extend TTL proportionally to active track count.
  // More active tracks means higher operational value; we keep data longer.
  const activeCount = snapshot.filter(
    (t) => t.lifecycle_state === 'CONFIRMED' || t.lifecycle_state === 'TRACKING' || t.lifecycle_state === 'DETECTED',
  ).length;
  const ttlSeconds = Math.min(
    REDIS_TARGETS_MAX_TTL_SECONDS,
    REDIS_TARGETS_TTL_SECONDS + activeCount * 600, // +10 min per active track, max 24h
  );
  await redisSet(REDIS_TARGETS_KEY, snapshot, ttlSeconds);
  if (!isRedisDisabledInThisProcess()) {
    state.lastVersion = await redisIncr(REDIS_TARGETS_VERSION_KEY);
  } else {
    state.lastVersion += 1;
  }
  invalidateMarkerDerivedCaches();
}

async function loadTargetsFromRedis(): Promise<TrackedTarget[] | null> {
  const targets = await redisGet<TrackedTarget[]>(REDIS_TARGETS_KEY);
  if (!targets || !Array.isArray(targets)) return null;
  try {
    const ver = await getRedis().get(REDIS_TARGETS_VERSION_KEY);
    getState().lastVersion = ver ? parseInt(ver, 10) : 0;
  } catch {
    /* Redis is optional in local/dev/build contexts. */
  }
  return targets
    .map(sanitizeTrackedTarget)
    .filter((target): target is TrackedTarget => Boolean(target));
}

async function seedTargetsFromRawEvidence(engine: TargetTrackerEngine): Promise<number> {
  const candidates = getRawMessages()
    .map(markerToCandidateEvent)
    .filter((c): c is CandidateEvent => Boolean(c))
    .sort((a, b) => a.ts - b.ts);
  for (const candidate of candidates) {
    engine.ingest(candidate);
  }
  return candidates.length;
}

async function doInit(): Promise<void> {
  const state = getState();
  const settings = loadSettings();
  const loaded = await loadTargetsFromRedis();
  const shouldSeedFromRaw = !loaded || loaded.length === 0;
  const engine = new TargetTrackerEngine(settings, { initialTargets: shouldSeedFromRaw ? [] : loaded });
  const seeded = shouldSeedFromRaw ? await seedTargetsFromRawEvidence(engine) : 0;
  state.engine = engine;
  state.initialized = true;
  if (seeded > 0 && engine.snapshot().length > 0) {
    await persistTargets();
  }
}

export async function initTargetStore(): Promise<void> {
  const state = getState();
  if (state.initialized) return;
  if (!state.initPromise) state.initPromise = doInit();
  await state.initPromise;
}

export async function syncTargetStoreFromRedis(): Promise<void> {
  const state = getState();
  if (isRedisDisabledInThisProcess()) return;
  const verRaw = await getRedis().get(REDIS_TARGETS_VERSION_KEY);
  const ver = verRaw ? parseInt(verRaw, 10) : 0;
  if (!ver || ver === state.lastVersion) return;
  const targets = await loadTargetsFromRedis();
  if (!targets) return;

  // P4-E: For targets whose EKF was lost or is very stale, warm up by replaying history
  for (const target of targets) {
    if (target.history.length < 3) continue;
    const age = Date.now() - target.last_seen;
    if (age > 10 * 60_000 && !target.ekf) {
      // Replay up to last 20 accepted observations through a fresh EKF
      const accepted = target.history
        .filter((h) => h.accepted)
        .slice(-20)
        .sort((a, b) => a.ts - b.ts);
      if (accepted.length >= 2) {
        const first = accepted[0]!;
        // P1-B: Use threat-specific EKF noise from trackMotionProfile, not hardcoded values.
        const ekfProfile = trackMotionProfile(target.threat_type);
        const ekf = new KalmanFilter2D(
          first.lat, first.lng, 0, 0, 0.5, 1e-3,
          ekfProfile.ekfProcessNoise,
          ekfProfile.ekfMeasurementNoise,
        );
        let prevTs = first.ts;
        for (let i = 1; i < accepted.length; i++) {
          const h = accepted[i]!;
          const dtSec = Math.max(0, (h.ts - prevTs) / 1000);
          if (dtSec > 0) ekf.predict(dtSec);
          ekf.update(h.lat, h.lng, h.confidence);
          prevTs = h.ts;
        }
        target.ekf = ekf;
      }
    }
  }

  state.engine = new TargetTrackerEngine(loadSettings(), { initialTargets: targets });
  state.lastVersion = ver;
  state.initialized = true;
  clearMarkerDerivedApiCachesLocal();
}

export async function ingestMarkerEvidence(marker: Record<string, unknown>): Promise<TrackerDecision | null> {
  await initTargetStore();
  const candidate = markerToCandidateEvent(marker);
  if (!candidate) return null;

  return withTargetWriteLock(async () => {
    const state = getState();
    if (!state.engine) state.engine = new TargetTrackerEngine(loadSettings());
    const decision = state.engine.ingest(candidate);
    if (decision.action !== 'REPLAY_SUPPRESSED') {
      await persistTargets();
    }
    return decision;
  });
}

export function getTrackedTargetRecords(): Record<string, unknown>[] {
  const nowMs = Date.now();
  return (getState().engine?.snapshot(nowMs) ?? [])
    .filter((target) => target.lifecycle_state !== 'REJECTED')
    .map((target) => targetToStoreRecord(target, nowMs));
}

export function getTrackedTargetsVersion(): number {
  return getState().lastVersion;
}

export async function clearTrackedTargetsByRegion(
  region: string,
  threatTypes?: string[],
  placeContains?: string,
): Promise<number> {
  await initTargetStore();
  return withTargetWriteLock(async () => {
    const state = getState();
    const engine = state.engine;
    if (!engine) return 0;
    const regionNorm = norm(region);
    const typeSet = new Set((threatTypes || []).map(norm).filter(Boolean));
    const placeNeedle = norm(placeContains);
    let changed = 0;
    for (const target of engine.snapshot()) {
      if (regionNorm && norm(target.region) !== regionNorm) continue;
      if (typeSet.size > 0 && !typeSet.has(norm(target.threat_type))) continue;
      if (placeNeedle && !norm(target.place).includes(placeNeedle)) continue;
      if (target.lifecycle_state === 'LOST' || target.lifecycle_state === 'DESTROYED' || target.lifecycle_state === 'REJECTED') {
        continue;
      }
      if (engine.markLifecycle(target.id, 'LOST')) changed += 1;
    }
    if (changed > 0) await persistTargets();
    return changed;
  });
}

export async function markTrackedTargetLifecycle(
  targetId: string,
  state: 'LOST' | 'DESTROYED' | 'STALE' | 'REJECTED',
): Promise<boolean> {
  await initTargetStore();
  return withTargetWriteLock(async () => {
    const engine = getState().engine;
    if (!engine) return false;
    const target = engine.markLifecycle(targetId, state);
    if (!target) return false;
    await persistTargets();
    return true;
  });
}

export async function updateTrackedTarget(
  targetId: string,
  updates: Record<string, unknown>,
): Promise<boolean> {
  await initTargetStore();
  return withTargetWriteLock(async () => {
    const engine = getState().engine;
    if (!engine) return false;
    const snapshot = engine.snapshot();
    const target = snapshot.find((t) => t.id === targetId);
    if (!target) return false;

    // Apply manual updates
    if (updates.lat !== undefined) target.lat = Number(updates.lat);
    if (updates.lng !== undefined) target.lng = Number(updates.lng);
    if (updates.count !== undefined) target.count = countOrOne(updates.count);
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

    // Persist through the engine instance (it uses Map internally, but we need to update the Map)
    // Actually, snapshot() returns copies. I need to update the actual target in the engine's Map.
    // I should add a method to the engine.
    const ok = engine.updateTargetAdministrative(targetId, updates);
    if (ok) await persistTargets();
    return ok;
  });
}

export function trackerDecisionToPublicRecord(decision: TrackerDecision | null): Record<string, unknown> | null {
  if (!decision?.target) return null;
  return targetToStoreRecord(decision.target);
}

// P5-D: Trajectory accuracy feedback
export async function recordTrajectoryFeedbackForTarget(
  targetId: string,
  actualLat: number,
  actualLng: number,
): Promise<boolean> {
  await initTargetStore();
  return withTargetWriteLock(async () => {
    const engine = getState().engine;
    if (!engine) return false;
    const ok = engine.recordTrajectoryFeedback(targetId, actualLat, actualLng);
    if (ok) await persistTargets();
    return ok;
  });
}

// P5-A: Predictive alarm — get pre-notification list
export function getTrackerPredictiveAlarms(
  regions: Array<{ id: string; lat: number; lng: number; radiusKm: number }>,
  horizonSec?: number,
): Array<{ targetId: string; regionId: string; etaSec: number; confidence: number }> {
  const engine = getState().engine;
  if (!engine) return [];
  return engine.getPredictiveAlarms(regions, horizonSec);
}

// ── Position Ticker ──────────────────────────────────────────────────────────

const TICK_INTERVAL_MS = 6_000;
const TICKER_GLOBAL_KEY = '__neptun_tracked_target_ticker__';
const REDIS_TICKER_LOCK_KEY = 'ticker:v3:lock';
const REDIS_TICKER_LOCK_TTL = 10;

let lastTickPositions = new Map<string, { lat: number; lng: number }>();

export function startTrackedTargetTicker(): void {
  if (isRedisDisabledInThisProcess()) return;
  if ((globalThis as Record<string, unknown>)[TICKER_GLOBAL_KEY]) return;
  (globalThis as Record<string, unknown>)[TICKER_GLOBAL_KEY] = true;

  setInterval(() => {
    try {
      tickTrackedTargets();
    } catch (err) {
      console.warn('[V3_TICKER] Error:', err);
    }
  }, TICK_INTERVAL_MS);

  // Periodic maintenance — every 5 minutes
  const MAINTENANCE_INTERVAL_MS = 5 * 60_000;
  setInterval(() => {
    try {
      const s = getState();
      if (!s.engine) return;
      // v3 maintenance
      s.engine.detectFormations();
      s.engine.enrichGeoContext();
      s.engine.detectAndMergeDuplicates();
      s.engine.deduplicateCrossChannelReposts();
      // v4 maintenance
      s.engine.computeSwarmCentroids();
      s.engine.computeCrossOblastCorrelation();
      s.engine.updateGhostPool();
      s.engine.reapStaleTracks();
      s.engine.inferLaunchOrigins();
    } catch (err) {
      console.warn('[MAINTENANCE] Error:', err);
    }
  }, MAINTENANCE_INTERVAL_MS);

  console.log(`[V3_TICKER] Position ticker started — ${TICK_INTERVAL_MS}ms interval`);
}

function tickTrackedTargets(): void {
  getRedis()
    .set(REDIS_TICKER_LOCK_KEY, String(process.pid), 'EX', REDIS_TICKER_LOCK_TTL, 'NX')
    .then((acquired) => {
      if (!acquired) return; // another worker holds the lock
      doTickTrackedTargets();
    })
    .catch((err) => console.warn('[V3_TICKER] lock error:', err));
}

function doTickTrackedTargets(): void {
  const state = getState();
  if (!state.engine) return;

  const now = Date.now();
  const snapshot = state.engine.snapshot(now);
  if (snapshot.length === 0) return;

  const batchUpdates: { track_id: string; mode: string; marker: Record<string, unknown> }[] = [];
  const currentTickPositions = new Map<string, { lat: number; lng: number }>();

  for (const target of snapshot) {
    if (
      target.lifecycle_state === 'REJECTED' ||
      target.lifecycle_state === 'DESTROYED' ||
      target.lifecycle_state === 'LOST' ||
      target.lifecycle_state === 'STALE'
    ) {
      continue;
    }

    const storeRecord = targetToStoreRecord(target, now);
    if (!storeRecord.is_estimated) continue; // Only tick actively moving targets

    const lat = storeRecord.lat as number;
    const lng = storeRecord.lng as number;

    currentTickPositions.set(target.id, { lat, lng });

    const prev = lastTickPositions.get(target.id);
    if (prev) {
      const dLat = Math.abs(prev.lat - lat);
      const dLng = Math.abs(prev.lng - lng);
      // Only broadcast if moved significantly (~5 meters)
      if (dLat > 0.00005 || dLng > 0.00005) {
        batchUpdates.push({
          track_id: target.id,
          mode: 'updated',
          marker: {
            id: target.id,
            lat,
            lng,
            speed_kmh: storeRecord.speed_kmh,
            course_bearing: storeRecord.course_bearing,
            ts: now,
            date: new Date(now).toISOString(),
          },
        });
      }
    } else {
      // First time we see it moving in a tick, record it but no need to broadcast a zero-delta update
    }
  }

  lastTickPositions = currentTickPositions;

  if (batchUpdates.length > 0) {
    broadcastSSE({ type: 'track_batch', data: { updates: batchUpdates } });
  }
}

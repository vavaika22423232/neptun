import {
  computeMarkerEventFingerprint,
  evaluateMarkerPublication,
  type MarkerPublicationDecision,
} from '@/lib/public-marker-policy';
import type { AdminSettings } from '@/lib/admin/data';
import { destinationPoint, haversineKm, normalizeEpochMs } from '@/lib/marker-movement-policy';
import { trackMotionProfile } from '@/lib/track-motion-profile';
import {
  buildTrackerRenderDescriptor,
  type TrackerEvent as RendererEvent,
} from '@/lib/drone-tracker-renderer';

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
  history: TargetHistoryItem[];
  event_fingerprints: string[];
  publication?: MarkerPublicationDecision;
  manual?: boolean;
  // ── Renderer output (applied after every create/update) ──────────────────
  is_loitering?: boolean;
  heading_confidence?: 'explicit' | 'track' | 'regional' | 'unknown';
  position_estimated?: boolean;
  eta_seconds?: number | null;
  display_confidence?: number;
  /** The rendered position may differ from raw lat/lng when back-projected */
  rendered_lat?: number;
  rendered_lng?: number;
  last_message_text?: string;
  last_resolve_status?: string;
  last_placement_mode?: string;
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
  const seed = [
    normalizeTrackId(event.upstream_track_id),
    norm(event.threat_type),
    norm(event.region),
    norm(event.place).slice(0, 16),
    normalizeCount(event.count),
    Math.round(event.lat * 10) / 10,
    Math.round(event.lng * 10) / 10,
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
  if (publication?.public) return 'CONFIRMED';
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
  // Young targets haven't moved far yet — reduce radius to prevent false merges
  if (target) {
    const ageMs = Math.max(0, event.ts - target.first_seen);
    if (ageMs < 5 * 60_000) return base * 0.6;   // < 5 min: 60% radius
    if (ageMs < 12 * 60_000) return base * 0.8;  // < 12 min: 80% radius
  }
  return base;
}

function impossibleMovement(target: TrackedTarget, event: CandidateEvent): { impossible: boolean; speedKmh: number; distKm: number } {
  const distKm = haversineKm(target.lat, target.lng, event.lat, event.lng);
  const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 1 / 3600);
  const speedKmh = distKm / dtHours;
  const profile = trackMotionProfile(event.threat_type);
  return {
    impossible: event.ts > target.last_seen && distKm > 4 && speedKmh > profile.maxSpeedKmh * 1.35,
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
    atTs <= target.last_seen
  ) {
    return { lat: target.lat, lng: target.lng, projected: false };
  }

  const profile = trackMotionProfile(target.threat_type);
  const elapsedMs = Math.min(Math.max(0, atTs - target.last_seen), profile.extrapolateMs);
  if (elapsedMs < 30_000) return { lat: target.lat, lng: target.lng, projected: false };

  const projectedKm = Math.min(speed, profile.maxSpeedKmh) * elapsedMs / 3_600_000;
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

function shouldHoldWeakMeasurement(
  target: TrackedTarget,
  event: CandidateEvent,
  confidence: number,
  rawDistKm: number,
): boolean {
  if (hasSameUpstreamTrack(target, event)) return false;
  if (rawDistKm < 3.5) return false;

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

  const diff = angularDiffDeg(previousBearing, observedBearing);
  if (diff > 150) return 52;
  if (diff > 120) return 32;
  if (diff > 90) return 20;
  if (diff > 60) return 10;
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
  const coastingWeight = minutes >= 10 ? 1.25 : minutes >= 5 ? 1.0 : 0.75;

  if (diff > 145) return 48 * coastingWeight;
  if (diff > 115) return 34 * coastingWeight;
  if (diff > 85) return 22 * coastingWeight;
  if (diff > 60) return 12 * coastingWeight;
  return 0;
}

export class TargetTrackerEngine {
  private readonly targets = new Map<string, TrackedTarget>();
  private readonly fingerprintIndex = new Map<string, { targetId: string; seenAt: number }>();

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
      sources: [...t.sources],
      history: [...t.history],
      event_fingerprints: [...t.event_fingerprints],
      movement_vector: { ...t.movement_vector },
      upstream_track_ids: [...t.upstream_track_ids],
    }));
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

    const target = this.findAssociation(normalizedEvent);
    if (target) {
      if (normalizedEvent.ts + 12_000 < target.last_seen) {
        this.appendHistory(target, normalizedEvent, fp, false, 'stale_replay', eventConf);
        this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: ts });
        return {
          action: 'EVENT_QUARANTINED',
          target,
          reason: 'stale_replay',
          fingerprint: fp,
          publication: policy,
        };
      }

      const movement = impossibleMovement(target, normalizedEvent);
      if (movement.impossible) {
        this.appendHistory(target, normalizedEvent, fp, false, 'impossible_movement', eventConf);
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
      this.updateTarget(target, normalizedEvent, fp, eventConf, policy);
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

    const created = this.createTarget(normalizedEvent, fp, eventConf, policy);
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

  private findAssociation(event: CandidateEvent): TrackedTarget | null {
    const eventCount = normalizeCount(event.count);
    let best: { target: TrackedTarget; score: number } | null = null;
    for (const target of this.targets.values()) {
      if (norm(target.threat_type) !== norm(event.threat_type)) continue;
      const currentLifecycle = lifecycleAt(target, event.ts);
      if (currentLifecycle === 'LOST' || currentLifecycle === 'DESTROYED' || currentLifecycle === 'REJECTED') {
        continue;
      }
      const sameUpstreamTrack = hasSameUpstreamTrack(target, event);
      if (hasDifferentExplicitGroup(target, event)) continue;
      if (target.region && event.region && norm(target.region) !== norm(event.region) && !sameUpstreamTrack) continue;
      // Per-target adaptive radius (young targets get tighter radius)
      let radiusKm = maxAssociationRadius(event, this.options, target);
      if (sameUpstreamTrack) {
        const profile = trackMotionProfile(event.threat_type);
        const dtHours = Math.max((event.ts - target.last_seen) / 3_600_000, 0);
        const trackIdMotionBudgetKm = Math.max(25, profile.nominalSpeedKmh * dtHours * 1.65);
        radiusKm = Math.min(90, Math.max(radiusKm, trackIdMotionBudgetKm));
      }
      const predicted = projectedTargetPosition(target, event.ts);
      const dist = haversineKm(predicted.lat, predicted.lng, event.lat, event.lng);
      if (dist > radiusKm) continue;
      const samePlace = target.place && event.place && norm(target.place) === norm(event.place);
      const countPenalty = target.count !== eventCount ? Math.min(18, Math.abs(target.count - eventCount) * 6) : 0;
      // Bearing penalty: threats moving in opposite directions should not merge
      const bearingPenalty = courseTurnPenalty(target, event);
      const corridorPenalty = courseCorridorPenalty(target, event);
      const innovationPenalty = movementInnovationPenalty(target, event, dist);
      const score = 100
        - (dist / radiusKm) * 65
        + (samePlace ? 12 : 0)
        + (sameUpstreamTrack ? 25 : 0)
        - countPenalty
        - bearingPenalty
        - corridorPenalty
        - innovationPenalty;
      if (score < associationScoreThreshold(target, event, !!samePlace)) continue;
      if (!best || score > best.score) best = { target, score };
    }
    return best?.target ?? null;
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

  private createTarget(
    event: CandidateEvent,
    fp: string,
    confidence: number,
    publication: MarkerPublicationDecision,
  ): TrackedTarget {
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
      last_message_text: typeof event.raw?.text === 'string' ? event.raw.text : undefined,
      last_resolve_status: typeof event.raw?.resolve_status === 'string' ? event.raw.resolve_status : undefined,
      last_placement_mode: typeof event.raw?.placement_mode === 'string' ? event.raw.placement_mode : undefined,
    };
    target.lifecycle_state = lifecycleFor(target, publication);
    this.appendHistory(target, event, fp, true, 'created', confidence);
    this._applyRendering(target);
    this.targets.set(target.id, target);
    this.fingerprintIndex.set(fp, { targetId: target.id, seenAt: event.ts });
    return target;
  }

  private updateTarget(
    target: TrackedTarget,
    event: CandidateEvent,
    fp: string,
    confidence: number,
    publication: MarkerPublicationDecision,
  ): void {
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

    target.lat = nextLat;
    target.lng = nextLng;
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
    target.speed_estimate_kmh = speed != null && Number.isFinite(speed) ? Math.round(speed) : null;
    target.movement_vector = {
      bearing_deg: bearing != null && Number.isFinite(bearing) ? Math.round(bearing) : null,
      speed_kmh: target.speed_estimate_kmh,
    };
    target.publication = publication;
    if (typeof event.raw?.text === 'string') target.last_message_text = event.raw.text;
    if (typeof event.raw?.resolve_status === 'string') target.last_resolve_status = event.raw.resolve_status;
    if (typeof event.raw?.placement_mode === 'string') target.last_placement_mode = event.raw.placement_mode;
    target.lifecycle_state = lifecycleFor(target, publication);
    this.appendHistory(target, event, fp, true, holdPosition ? 'updated_position_held' : 'updated', confidence);
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
    target.history.push({
      fingerprint: fp,
      ts: event.ts,
      lat: event.lat,
      lng: event.lng,
      source: norm(event.source) || 'unknown',
      ...(channelPriority !== undefined && { channel_priority: channelPriority }),
      ...(count > 1 && { count }),
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
      };

      const desc = buildTrackerRenderDescriptor(currentEvent);

      target.is_loitering = desc.is_loitering;
      target.heading_confidence = desc.heading_confidence;
      target.position_estimated = desc.position_estimated ?? false;
      target.eta_seconds = desc.eta_seconds;
      target.display_confidence = desc.display_confidence;

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
    } catch {
      // Never let rendering errors break the tracker
    }
  }
}

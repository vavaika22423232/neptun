import {
  destinationPoint,
  haversineKm,
  normalizeEpochMs,
  resolveTickerBearing,
} from '@/lib/marker-movement-policy';
import { trackMotionProfile } from '@/lib/track-motion-profile';
import { snapToCorridor } from '@/lib/nav-graph';

export type TrackEstimateState =
  | 'observed'
  | 'extrapolated'
  | 'stale'
  | 'lost'
  | 'static'
  | 'manual'
  | 'split_candidate'
  | 'terrain_masking';

export type TrackEstimate = {
  state: TrackEstimateState;
  lat: number;
  lng: number;
  confidence: number;
  visualConfidence: number;
  speedKmh: number;
  bearingDeg: number | null;
  lastObservationMs: number;
  ageMs: number;
  isEstimated: boolean;
  reason: string;
};

export type RealisticTickDecision =
  | {
      shouldTick: true;
      reason: 'estimate_tick';
      nextLat: number;
      nextLng: number;
      speedKmh: number;
      bearingDeg: number;
      distKm: number;
      estimate: TrackEstimate;
    }
  | {
      shouldTick: false;
      reason:
        | 'static'
        | 'manual'
        | 'lost'
        | 'stale'
        | 'terrain_masking'
        | 'invalid_motion'
        | 'invalid_coords'
        | 'near_target';
      estimate: TrackEstimate;
    };

export type TrackObservationAction =
  | 'accept_position'
  | 'hold_position'
  | 'split_candidate'
  | 'observation_only';

export type TrackObservationReason =
  | 'accepted'
  | 'stale_observation'
  | 'teleport_blocked_split_candidate'
  | 'weak_geo_hold'
  | 'invalid_coords';

export type TrackObservationDecision = {
  action: TrackObservationAction;
  reason: TrackObservationReason;
  jumpDistKm: number;
  antiTeleportKm: number;
  maxPlausibleSpeedKmh: number;
  lastObservationMs: number;
  newObservationMs: number;
  staleObservationReplay: boolean;
  weakGeoHold: boolean;
};

type LatLngTs = { lat: number; lng: number; ts?: number };

const STATIC_THREAT_TYPES = new Set([
  'explosion', 'vibuh', 'alert', 'allclear', 'chemical', 'nuclear',
  'artillery', 'obstril', 'info',
]);

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

function numericConfidence(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export { trackMotionProfile };

function markerBaseConfidence(marker: Record<string, unknown>): number {
  const c100 = Number(marker.confidence_0_100);
  if (Number.isFinite(c100) && c100 > 0) return clamp01(c100 / 100);
  const c = Number(marker.confidence);
  if (Number.isFinite(c) && c > 0) return clamp01(c > 1 ? c / 100 : c);
  return 0.68;
}

function lastObservation(marker: Record<string, unknown>): LatLngTs | null {
  const obs = marker.observations as LatLngTs[] | undefined;
  if (obs && obs.length > 0) return obs[obs.length - 1];
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng, ts: Number(marker.created_at_epoch) || undefined };
}

export function estimateTrackState(marker: Record<string, unknown>, nowMs: number): TrackEstimate {
  const threatType = String(marker.threat_type || '');
  const profile = trackMotionProfile(threatType);
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  const fallbackEstimate: TrackEstimate = {
    state: 'lost',
    lat: Number.isFinite(lat) ? lat : 0,
    lng: Number.isFinite(lng) ? lng : 0,
    confidence: 0,
    visualConfidence: 0,
    speedKmh: 0,
    bearingDeg: null,
    lastObservationMs: nowMs,
    ageMs: 0,
    isEstimated: false,
    reason: 'invalid_coords',
  };

  if (STATIC_THREAT_TYPES.has(threatType)) return { ...fallbackEstimate, state: 'static', reason: 'static_type' };
  if (marker.manual) return { ...fallbackEstimate, state: 'manual', reason: 'manual' };

  const obs = lastObservation(marker);
  if (!obs) return fallbackEstimate;
  const lastObservationMs = normalizeEpochMs(Number(obs.ts) || 0, nowMs);
  const ageMs = Math.max(0, nowMs - lastObservationMs);
  const baseConfidence = markerBaseConfidence(marker);
  const confidence = clamp01(baseConfidence * Math.pow(0.5, ageMs / profile.confidenceHalfLifeMs));
  const bearingDeg = resolveTickerBearing(marker);
  const rawSpeed = Number(marker.speed_kmh) || Number(marker.computed_speed_kmh) || profile.nominalSpeedKmh;
  const speedKmh = Math.max(0, Math.min(rawSpeed, profile.maxSpeedKmh));

  let state: TrackEstimateState = 'observed';
  let reason = 'fresh_observation';
  if (ageMs > profile.lostMs) {
    state = 'lost';
    reason = 'lost_ttl';
  } else if (ageMs > profile.staleMs) {
    state = 'stale';
    reason = 'stale_ttl';
  } else if (ageMs > profile.observedFreshMs) {
    state = ageMs <= profile.extrapolateMs && bearingDeg != null && speedKmh > 0 ? 'extrapolated' : 'stale';
    reason = state === 'extrapolated' ? 'motion_extrapolated' : 'no_motion_for_extrapolation';
  }

  // Terrain masking for low-altitude threats (UAVs, cruise missiles)
  if (state === 'stale' && (profile.nominalAltitudeMeters || 1000) <= 500) {
    if (ageMs <= profile.extrapolateMs + 10 * 60_000) {
      state = 'terrain_masking';
      reason = 'terrain_masking_ttl';
    }
  }

  let estimateLat = Number(obs.lat);
  let estimateLng = Number(obs.lng);
  const canMove = (state === 'extrapolated' || state === 'terrain_masking') && bearingDeg != null && speedKmh > 0;
  if (canMove) {
    const dtHours = Math.min(ageMs, profile.extrapolateMs) / 3_600_000;
    const VISUAL_SPEED_MULTIPLIER = 0.35; // Keep synced with MapLibreContainer.tsx
    const distKm = speedKmh * dtHours * VISUAL_SPEED_MULTIPLIER;
    
    // P6-C: Topographic corridor snapping
    let trajectory = marker.trajectory as { end?: [number, number] } | undefined;
    if (!trajectory?.end && bearingDeg != null) {
      const inferred = inferBayesianTarget(estimateLat, estimateLng, bearingDeg);
      if (inferred) trajectory = { end: inferred };
    }
    const snapped = snapToCorridor(estimateLat, estimateLng, bearingDeg, distKm, trajectory?.end);
    if (snapped) {
      estimateLat = snapped.lat;
      estimateLng = snapped.lng;
    } else {
      [estimateLat, estimateLng] = destinationPoint(estimateLat, estimateLng, bearingDeg, distKm);
    }
  }

  return {
    state,
    lat: estimateLat,
    lng: estimateLng,
    confidence,
    visualConfidence: state === 'observed' ? confidence : state === 'extrapolated' ? confidence * 0.85 : state === 'terrain_masking' ? confidence * 0.40 : confidence * 0.60,
    speedKmh,
    bearingDeg,
    lastObservationMs,
    ageMs,
    isEstimated: state === 'extrapolated' || state === 'terrain_masking',
    reason,
  };
}

export function decideTrackObservationUpdate(input: {
  existing: Record<string, unknown>;
  incoming: Record<string, unknown>;
  nowMs: number;
}): TrackObservationDecision {
  const existingLat = Number(input.existing.lat);
  const existingLng = Number(input.existing.lng);
  const newLat = Number(input.incoming.lat);
  const newLng = Number(input.incoming.lng);
  const threatType = String(input.existing.threat_type || input.incoming.threat_type || '');
  const profile = trackMotionProfile(threatType);
  const observations = input.existing.observations as Array<{ ts?: number }> | undefined;
  const rawLastTs = observations && observations.length > 0
    ? Number(observations[observations.length - 1].ts) || 0
    : Number(input.existing.created_at_epoch) || 0;
  const lastObservationMs = normalizeEpochMs(rawLastTs, input.nowMs);
  const newObservationMs = normalizeEpochMs(Number(input.incoming.created_at_epoch) || 0, input.nowMs);
  const staleObservationReplay = newObservationMs + 12_000 < lastObservationMs;
  const prevConf = numericConfidence(input.existing.confidence);
  const incConf = numericConfidence(input.incoming.confidence);
  const invalidCoords =
    !Number.isFinite(existingLat) ||
    !Number.isFinite(existingLng) ||
    !Number.isFinite(newLat) ||
    !Number.isFinite(newLng);
  const currentSpeed = Number(input.existing.computed_speed_kmh) || Number(input.existing.speed_kmh) || profile.nominalSpeedKmh;
  const hoursSinceLastObs = Math.max((input.nowMs - lastObservationMs) / 3_600_000, 0.01);
  const speedForCalc = currentSpeed > 0 ? Math.min(currentSpeed * 1.5, profile.maxSpeedKmh) : profile.maxSpeedKmh;
  const antiTeleportKm = Math.max(speedForCalc * hoursSinceLastObs * 1.5, 25);
  const jumpDistKm = invalidCoords ? 0 : haversineKm(existingLat, existingLng, newLat, newLng);
  const weakGeoHold =
    !staleObservationReplay &&
    !invalidCoords &&
    jumpDistKm >= 3.5 &&
    incConf != null &&
    prevConf != null &&
    incConf < prevConf - 0.15 &&
    incConf < 0.42;

  let action: TrackObservationAction = 'accept_position';
  let reason: TrackObservationReason = 'accepted';
  if (invalidCoords) {
    action = 'observation_only';
    reason = 'invalid_coords';
  } else if (staleObservationReplay) {
    action = 'observation_only';
    reason = 'stale_observation';
  } else if (jumpDistKm > antiTeleportKm) {
    action = 'split_candidate';
    reason = 'teleport_blocked_split_candidate';
  } else if (weakGeoHold) {
    action = 'hold_position';
    reason = 'weak_geo_hold';
  }

  return {
    action,
    reason,
    jumpDistKm,
    antiTeleportKm,
    maxPlausibleSpeedKmh: profile.maxSpeedKmh,
    lastObservationMs,
    newObservationMs,
    staleObservationReplay,
    weakGeoHold,
  };
}

const MAJOR_CITIES: Record<string, [number, number]> = {
  'Kyiv': [50.4501, 30.5234],
  'Kharkiv': [49.9935, 36.2304],
  'Odesa': [46.4825, 30.7233],
  'Dnipro': [48.4647, 35.0462],
  'Lviv': [49.8397, 24.0297],
  'Zaporizhzhia': [47.8388, 35.1396],
  'Kryvyi Rih': [47.9105, 33.3918],
  'Mykolaiv': [46.9750, 31.9946],
  'Vinnytsia': [49.2322, 28.4687],
  'Poltava': [49.5895, 34.5513],
  'Zhytomyr': [50.2547, 28.6586],
  'Cherkasy': [49.4444, 32.0598],
  'Khmelnytskyi': [49.4230, 26.9871],
  'Chernivtsi': [49.2920, 25.9328],
  'Sumy': [50.9077, 34.7981],
  'Rivne': [50.6199, 26.2516],
  'Ivano-Frankivsk': [48.9226, 24.7111],
  'Ternopil': [49.5535, 25.5948],
  'Lutsk': [50.6199, 25.3254],
};

function inferBayesianTarget(lat: number, lng: number, currentBearing: number): [number, number] | null {
  let bestCity: string | null = null;
  let bestScore = -Infinity;

  for (const [city, coords] of Object.entries(MAJOR_CITIES)) {
    const dist = haversineKm(lat, lng, coords[0], coords[1]);
    if (dist < 10 || dist > 800) continue; // Too close or too far
    
    // Bearing to city
    const dLng = (coords[1] - lng) * (Math.PI / 180);
    const l1 = lat * (Math.PI / 180);
    const l2 = coords[0] * (Math.PI / 180);
    const y = Math.sin(dLng) * Math.cos(l2);
    const x = Math.cos(l1) * Math.sin(l2) - Math.sin(l1) * Math.cos(l2) * Math.cos(dLng);
    const targetBearing = (Math.atan2(y, x) * (180 / Math.PI) + 360) % 360;

    let diff = Math.abs(currentBearing - targetBearing);
    if (diff > 180) diff = 360 - diff;

    // We want diff to be small. Bayesian prior: closer cities slightly more probable.
    // Score combines angular alignment and distance
    const angularScore = Math.exp(-diff / 15.0); // sharp dropoff if off by more than 15 degrees
    const distancePrior = Math.exp(-dist / 500.0); // slight preference for closer targets
    const score = angularScore * distancePrior;

    if (score > bestScore && score > 0.3) {
      bestScore = score;
      bestCity = city;
    }
  }

  if (bestCity) {
    return MAJOR_CITIES[bestCity];
  }
  return null;
}

export function decideRealisticTickerStep(input: {
  marker: Record<string, unknown>;
  nowMs: number;
  tickIntervalMs: number;
}): RealisticTickDecision {
  const estimate = estimateTrackState(input.marker, input.nowMs);
  if (estimate.state === 'static') return { shouldTick: false, reason: 'static', estimate };
  if (estimate.state === 'manual') return { shouldTick: false, reason: 'manual', estimate };
  if (estimate.state === 'lost') return { shouldTick: false, reason: 'lost', estimate };
  if (estimate.state === 'stale') return { shouldTick: false, reason: 'stale', estimate };
  if (estimate.bearingDeg == null || estimate.speedKmh <= 0) return { shouldTick: false, reason: 'invalid_motion', estimate };

  const curLat = Number(input.marker.lat);
  const curLng = Number(input.marker.lng);
  if (!Number.isFinite(curLat) || !Number.isFinite(curLng)) return { shouldTick: false, reason: 'invalid_coords', estimate };

  const profile = trackMotionProfile(String(input.marker.threat_type || ''));
  let trajectory = input.marker.trajectory as { end?: [number, number] } | undefined;
  
  if (!trajectory?.end && estimate.bearingDeg != null) {
    const inferred = inferBayesianTarget(curLat, curLng, estimate.bearingDeg);
    if (inferred) {
      trajectory = trajectory ? { ...trajectory, end: inferred } : { end: inferred };
    }
  }

  const dtHours = input.tickIntervalMs / 3_600_000;
  const distKm = estimate.speedKmh * dtHours;
  if (trajectory?.end) {
    const distToEnd = haversineKm(curLat, curLng, trajectory.end[0], trajectory.end[1]);
    if (distToEnd <= Math.max(profile.targetStopKm, distKm * 1.2)) {
      return { shouldTick: false, reason: 'near_target', estimate };
    }
  }

  const [nextLat, nextLng] = destinationPoint(curLat, curLng, estimate.bearingDeg, distKm);
  const snapped = snapToCorridor(curLat, curLng, estimate.bearingDeg, distKm, trajectory?.end);
  
  return {
    shouldTick: true,
    reason: 'estimate_tick',
    nextLat: snapped ? snapped.lat : nextLat,
    nextLng: snapped ? snapped.lng : nextLng,
    speedKmh: estimate.speedKmh,
    bearingDeg: snapped ? snapped.newBearingDeg : estimate.bearingDeg,
    distKm,
    estimate,
  };
}

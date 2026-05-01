import { trackMotionProfile } from '@/lib/track-motion-profile';

export type PositionUpdateAction = 'accept_position' | 'hold_position';

export type PositionUpdateDecision = {
  action: PositionUpdateAction;
  reason: 'accepted' | 'stale_observation' | 'teleport_blocked' | 'weak_geo_hold';
  jumpDistKm: number;
  antiTeleportKm: number;
  staleObservationReplay: boolean;
  weakGeoHold: boolean;
  maxPlausibleSpeedKmh: number;
  lastObservationMs: number;
  newObservationMs: number;
};

export type TickDecision =
  | { shouldTick: true; reason: 'tick'; nextLat: number; nextLng: number; speedKmh: number; bearingDeg: number; distKm: number }
  | { shouldTick: false; reason: 'static_type' | 'manual' | 'stale_real_observation' | 'invalid_motion' | 'invalid_coords' | 'near_target' };

type LatLng = { lat: number; lng: number };

const STATIC_THREAT_TYPES = new Set([
  'explosion', 'vibuh', 'alert', 'allclear', 'chemical', 'nuclear',
  'artillery', 'obstril', 'info',
]);

function motionProfile(threatType: string) {
  const profile = trackMotionProfile(threatType);
  return {
    maxSpeedKmh: profile.maxSpeedKmh,
    tickTtlMs: profile.extrapolateMs,
    targetStopKm: profile.targetStopKm,
  };
}

export function normalizeEpochMs(ts: number, fallbackMs: number): number {
  if (!Number.isFinite(ts) || ts <= 0) return fallbackMs;
  return ts > 10_000_000_000 ? Math.round(ts) : Math.round(ts * 1000);
}

export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function destinationPoint(lat: number, lng: number, bearingDeg: number, distKm: number): [number, number] {
  const R = 6371;
  const toRad = Math.PI / 180;
  const lat1 = lat * toRad;
  const lng1 = lng * toRad;
  const brg = bearingDeg * toRad;
  const d = distKm / R;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(d) +
    Math.cos(lat1) * Math.sin(d) * Math.cos(brg),
  );
  const lng2 = lng1 + Math.atan2(
    Math.sin(brg) * Math.sin(d) * Math.cos(lat1),
    Math.cos(d) - Math.sin(lat1) * Math.sin(lat2),
  );

  return [lat2 / toRad, lng2 / toRad];
}

export function maxPlausibleSpeedKmh(threatType: string): number {
  return motionProfile(threatType).maxSpeedKmh;
}

export function decidePositionUpdate(input: {
  existingLat: number;
  existingLng: number;
  newLat: number;
  newLng: number;
  threatType: string;
  currentSpeedKmh: number;
  existingConfidence?: number;
  incomingConfidence?: number;
  lastObservationTs: number;
  newObservationTs: number;
  nowMs: number;
}): PositionUpdateDecision {
  const lastObservationMs = normalizeEpochMs(input.lastObservationTs, input.nowMs);
  const newObservationMs = normalizeEpochMs(input.newObservationTs, input.nowMs);
  const staleObservationReplay = newObservationMs + 12_000 < lastObservationMs;
  const hoursSinceLastObs = Math.max((input.nowMs - lastObservationMs) / 3_600_000, 0.01);
  const maxSpeed = maxPlausibleSpeedKmh(input.threatType);
  const currentSpeed = Number.isFinite(input.currentSpeedKmh) ? Math.max(0, input.currentSpeedKmh) : 0;
  const speedForCalc = currentSpeed > 0 ? Math.min(currentSpeed * 1.5, maxSpeed) : maxSpeed;
  const antiTeleportKm = Math.max(speedForCalc * hoursSinceLastObs * 1.5, 25);
  const jumpDistKm = haversineKm(input.existingLat, input.existingLng, input.newLat, input.newLng);
  const positionRejected = jumpDistKm > antiTeleportKm;
  const prevConf = input.existingConfidence;
  const incConf = input.incomingConfidence;
  const weakGeoHold =
    !positionRejected &&
    jumpDistKm >= 3.5 &&
    incConf != null &&
    prevConf != null &&
    incConf < prevConf - 0.15 &&
    incConf < 0.42;

  const reason = staleObservationReplay
    ? 'stale_observation'
    : positionRejected
      ? 'teleport_blocked'
      : weakGeoHold
        ? 'weak_geo_hold'
        : 'accepted';

  return {
    action: reason === 'accepted' ? 'accept_position' : 'hold_position',
    reason,
    jumpDistKm,
    antiTeleportKm,
    staleObservationReplay,
    weakGeoHold,
    maxPlausibleSpeedKmh: maxSpeed,
    lastObservationMs,
    newObservationMs,
  };
}

export function smoothObservedSpeedKmh(input: {
  prev: LatLng;
  curr: LatLng;
  prevTs: number;
  currTs: number;
  threatType: string;
  previousComputedSpeedKmh?: number;
  nowMs: number;
}): number | null {
  const prevMs = normalizeEpochMs(input.prevTs, input.nowMs);
  const currMs = normalizeEpochMs(input.currTs, input.nowMs);
  const dtHours = (currMs - prevMs) / 3_600_000;
  if (dtHours <= 0.001) return null;
  const distKm = haversineKm(input.prev.lat, input.prev.lng, input.curr.lat, input.curr.lng);
  if (distKm <= 1) return null;
  const rawSpeed = Math.round(distKm / dtHours);
  if (rawSpeed < 50 || rawSpeed > maxPlausibleSpeedKmh(input.threatType)) return null;
  const prevComputed = input.previousComputedSpeedKmh;
  if (prevComputed && prevComputed > 0) {
    const alpha = 0.4;
    return Math.round((alpha * rawSpeed) + ((1 - alpha) * prevComputed));
  }
  return rawSpeed;
}

function bearingFromPoints(a: LatLng, b: LatLng): number | null {
  const dLat = b.lat - a.lat;
  const midLat = (a.lat + b.lat) / 2;
  const cosLat = Math.cos(midLat * Math.PI / 180);
  const dLng = (b.lng - a.lng) * cosLat;
  if (Math.abs(dLat) <= 0.0001 && Math.abs(dLng) <= 0.0001) return null;
  return (Math.atan2(dLng, dLat) * (180 / Math.PI) + 360) % 360;
}

export function resolveTickerBearing(marker: Record<string, unknown>): number | null {
  const tickerBearing = marker.ticker_bearing;
  if (typeof tickerBearing === 'number' && Number.isFinite(tickerBearing)) return tickerBearing;

  const trajectory = marker.trajectory as { start?: number[]; end?: number[] } | undefined;
  if (trajectory?.start && trajectory?.end) {
    const bearing = bearingFromPoints(
      { lat: trajectory.start[0], lng: trajectory.start[1] },
      { lat: trajectory.end[0], lng: trajectory.end[1] },
    );
    if (bearing != null) return bearing;
  }

  const obs = (marker.observations as Array<{ lat: number; lng: number }> | undefined) ||
    (marker.positions as Array<{ lat: number; lng: number }> | undefined);
  if (obs && obs.length >= 2) {
    const prev = obs[obs.length - 2];
    const last = obs[obs.length - 1];
    const bearing = bearingFromPoints(prev, last);
    if (bearing != null) return bearing;
  }

  const courseBearing = marker.course_bearing;
  if (typeof courseBearing === 'number' && Number.isFinite(courseBearing)) return courseBearing;
  return null;
}

export function decideTickerStep(input: {
  marker: Record<string, unknown>;
  nowMs: number;
  tickIntervalMs: number;
}): TickDecision {
  const threatType = String(input.marker.threat_type || '');
  if (STATIC_THREAT_TYPES.has(threatType)) return { shouldTick: false, reason: 'static_type' };
  if (input.marker.manual) return { shouldTick: false, reason: 'manual' };

  const obs = input.marker.observations as Array<{ ts: number }> | undefined;
  const lastRawTs = obs && obs.length > 0 ? obs[obs.length - 1].ts : input.marker.created_at_epoch as number;
  const lastRealMs = normalizeEpochMs(Number(lastRawTs) || 0, input.nowMs);
  const profile = motionProfile(threatType);
  if (input.nowMs - lastRealMs > profile.tickTtlMs) {
    return { shouldTick: false, reason: 'stale_real_observation' };
  }

  const rawSpeed = Number(input.marker.speed_kmh) || Number(input.marker.computed_speed_kmh) || 0;
  const bearing = resolveTickerBearing(input.marker);
  if (rawSpeed <= 0 || bearing == null) return { shouldTick: false, reason: 'invalid_motion' };

  const curLat = Number(input.marker.lat);
  const curLng = Number(input.marker.lng);
  if (!Number.isFinite(curLat) || !Number.isFinite(curLng)) return { shouldTick: false, reason: 'invalid_coords' };

  const speedKmh = Math.min(rawSpeed, profile.maxSpeedKmh);
  const dtHours = input.tickIntervalMs / 3_600_000;
  const distKm = speedKmh * dtHours;

  const trajectory = input.marker.trajectory as { end?: [number, number] } | undefined;
  if (trajectory?.end) {
    const distToEnd = haversineKm(curLat, curLng, trajectory.end[0], trajectory.end[1]);
    if (distToEnd <= Math.max(profile.targetStopKm, distKm * 1.2)) {
      return { shouldTick: false, reason: 'near_target' };
    }
  }

  const [nextLat, nextLng] = destinationPoint(curLat, curLng, bearing, distKm);
  return { shouldTick: true, reason: 'tick', nextLat, nextLng, speedKmh, bearingDeg: bearing, distKm };
}

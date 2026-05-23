/**
 * Resolve geographic bearing (0° = N, 90° = E, clockwise) for threat markers.
 */
import type { Marker, Trajectory } from '@/types';
import { haversineKm } from '@/lib/track-sanitize';

const DEG = Math.PI / 180;

/** Minimum ground distance (km) between two track points to infer bearing (noise filter). */
const MIN_TRACK_SEGMENT_KM = 0.45;

const CARDINAL_UK: Record<string, number> = {
  захід: 270,
  заходу: 270,
  західного: 270,
  західн: 270,
  північ: 0,
  півночі: 0,
  північного: 0,
  північн: 0,
  схід: 90,
  сходу: 90,
  східного: 90,
  східн: 90,
  південь: 180,
  півдня: 180,
  південного: 180,
  південн: 180,
  'північний захід': 315,
  'північного заходу': 315,
  'північний схід': 45,
  'північного сходу': 45,
  'південний захід': 225,
  'південного заходу': 225,
  'південний схід': 135,
  'південного сходу': 135,
};

/**
 * Initial bearing from (lat1,lng1) to (lat2,lng2), degrees 0–360 (0 = north, clockwise).
 */
export function initialBearingDeg(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const φ1 = lat1 * DEG;
  const φ2 = lat2 * DEG;
  const Δλ = (lng2 - lng1) * DEG;
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  let θ = (Math.atan2(y, x) * 180) / Math.PI;
  θ = (θ + 360) % 360;
  return θ;
}

function normalizeBearing(v: unknown): number | null {
  if (typeof v !== 'number' || !Number.isFinite(v)) return null;
  return ((v % 360) + 360) % 360;
}

function bearingFromPositions(marker: Marker): number | null {
  const pts = marker.positions;
  if (!pts?.length || pts.length < 2) return null;
  const sorted = [...pts].sort((a, b) => a.ts - b.ts);
  for (let i = sorted.length - 1; i > 0; i--) {
    const a = sorted[i - 1];
    const b = sorted[i];
    if (!Number.isFinite(a.lat) || !Number.isFinite(a.lng) || !Number.isFinite(b.lat) || !Number.isFinite(b.lng)) {
      continue;
    }
    const d = haversineKm(a.lat, a.lng, b.lat, b.lng);
    if (d >= MIN_TRACK_SEGMENT_KM) {
      return initialBearingDeg(a.lat, a.lng, b.lat, b.lng);
    }
  }
  return null;
}

function bearingFromTrajectory(marker: Marker, traj: Trajectory): number | null {
  const curLat = marker.lat;
  const curLng = marker.lng;
  const end = traj.end;
  const start = traj.start;
  const wps = traj.waypoints;

  if (end && Number.isFinite(end[0]) && Number.isFinite(end[1])) {
    const toEnd = haversineKm(curLat, curLng, end[0], end[1]);
    if (toEnd >= MIN_TRACK_SEGMENT_KM) {
      return initialBearingDeg(curLat, curLng, end[0], end[1]);
    }
  }

  if (wps && wps.length >= 2) {
    const a = wps[wps.length - 2];
    const b = wps[wps.length - 1];
    if (
      a &&
      b &&
      Number.isFinite(a[0]) &&
      Number.isFinite(a[1]) &&
      Number.isFinite(b[0]) &&
      Number.isFinite(b[1])
    ) {
      const d = haversineKm(a[0], a[1], b[0], b[1]);
      if (d >= MIN_TRACK_SEGMENT_KM) {
        return initialBearingDeg(a[0], a[1], b[0], b[1]);
      }
    }
  }

  if (
    start &&
    end &&
    Number.isFinite(start[0]) &&
    Number.isFinite(start[1]) &&
    Number.isFinite(end[0]) &&
    Number.isFinite(end[1])
  ) {
    const d = haversineKm(start[0], start[1], end[0], end[1]);
    if (d >= MIN_TRACK_SEGMENT_KM) {
      return initialBearingDeg(start[0], start[1], end[0], end[1]);
    }
  }

  return null;
}

function bearingFromTrackerTarget(marker: Marker): number | null {
  const target = marker.tracker_target;
  if (!target || target.length < 2) return null;
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  const targetLat = Number(target[0]);
  const targetLng = Number(target[1]);
  if (
    !Number.isFinite(lat) ||
    !Number.isFinite(lng) ||
    !Number.isFinite(targetLat) ||
    !Number.isFinite(targetLng)
  ) {
    return null;
  }
  const dist = haversineKm(lat, lng, targetLat, targetLng);
  if (dist < MIN_TRACK_SEGMENT_KM) return null;
  return initialBearingDeg(lat, lng, targetLat, targetLng);
}

function bearingFromCardinalText(raw: string | undefined): number | null {
  if (!raw || typeof raw !== 'string') return null;
  const key = raw.toLowerCase().trim();
  if (CARDINAL_UK[key] != null) return CARDINAL_UK[key];
  for (const [k, brg] of Object.entries(CARDINAL_UK)) {
    if (key.includes(k)) return brg;
  }
  return null;
}

/**
 * Best-effort true bearing for the threat movement direction.
 */
export function resolveThreatBearingDeg(marker: Marker): number | null {
  const preferTargetBearing =
    marker.last_observation_quality === 'target_hint' ||
    marker.tracker_truth?.coordinate_role === 'target' ||
    marker.tracker_truth?.public_position_policy === 'hold_existing' ||
    marker.placement_mode === 'target_only_no_current_position' ||
    marker.resolve_status === 'trajectory_approach' ||
    marker.resolve_status === 'predictive_approach';

  if (preferTargetBearing) {
    const traj = marker.trajectory;
    if (traj) {
      const fromTraj = bearingFromTrajectory(marker, traj);
      if (fromTraj != null) return fromTraj;
    }
    const fromTrackerTarget = bearingFromTrackerTarget(marker);
    if (fromTrackerTarget != null) return fromTrackerTarget;
  }

  const fromTrack = bearingFromPositions(marker);
  if (fromTrack != null) return fromTrack;

  const traj = marker.trajectory;
  if (traj) {
    const fromTraj = bearingFromTrajectory(marker, traj);
    if (fromTraj != null) return fromTraj;
  }

  const cb = normalizeBearing(marker.course_bearing);
  if (cb != null) return cb;

  const tb = normalizeBearing(marker.ticker_bearing);
  if (tb != null) return tb;

  const fromCourse = bearingFromCardinalText(marker.course_direction);
  if (fromCourse != null) return fromCourse;

  const fromArrow = bearingFromCardinalText(marker.arrow_direction);
  if (fromArrow != null) return fromArrow;

  return null;
}

/**
 * CSS `transform: rotate()` for web threat rasters (shahed3.webp, PNG/SVG missiles).
 * True bearing 0° = north, clockwise; icon nose in assets points “up” (north) when rotate(0).
 * Keep in sync with Flutter `canvasRotationRadMatchingWeb`.
 */
export function bearingToWebIconRotationCssDeg(bearingDeg: number): number {
  return ((bearingDeg % 360) + 360) % 360;
}

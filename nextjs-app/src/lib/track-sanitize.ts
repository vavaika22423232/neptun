/**
 * Track / trajectory sanitization for API output and client animation.
 * Drops timestamp glitches and impossible jumps so trails, arrows, and speeds stay coherent.
 */
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';

/** Server + client safe — used by build-markers and MapContainer (do not import build-markers from client). */
export function maxSpeedKmhForThreatType(tt: string): number {
  if (tt === 'ballistic') return 6000;
  if (['missile', 'raketa', 'pusk', 'launch', 'krylata'].includes(tt)) return 1400;
  if (tt === 'kab' || tt === 'rszv') return 1100;
  if (tt === 'avia') return 1000;
  return 420;
}

export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export type SanitizeTrackPoint = {
  lat: number;
  lng: number;
  ts: number;
  source?: string;
};

/** Max single hop between trajectory polyline vertices (km) by threat class. */
export function maxWaypointSegmentKmForThreat(threatType: string): number {
  const tt = threatType || 'default';
  if (tt === 'ballistic') return 2800;
  if (['missile', 'raketa', 'pusk', 'launch', 'krylata'].includes(tt)) return 950;
  if (tt === 'kab' || tt === 'rszv') return 380;
  if (tt === 'avia') return 850;
  return 240;
}

/** Max plausible straight-line distance start→end for a single rendered threat arc (km). */
export function maxTrajectoryChordKmForThreat(threatType: string): number {
  const tt = threatType || 'default';
  if (tt === 'ballistic') return 5200;
  if (['missile', 'raketa', 'pusk', 'launch', 'krylata'].includes(tt)) return 2400;
  if (tt === 'avia') return 1600;
  return 950;
}

function cleanCoordPair(p: unknown): [number, number] | undefined {
  if (!Array.isArray(p) || p.length < 2) return undefined;
  const lat = Number(p[0]);
  const lng = Number(p[1]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return undefined;
  if (!isPlausibleThreatCoordinate(lat, lng)) return undefined;
  return [lat, lng];
}

/**
 * Filter waypoint chain: plausible coords only, no absurd segment jumps for this threat type.
 */
export function sanitizeTrajectoryWaypoints(
  waypoints: [number, number][] | undefined,
  threatType: string,
): [number, number][] | undefined {
  if (!waypoints?.length) return undefined;
  const maxSeg = maxWaypointSegmentKmForThreat(threatType);
  const out: [number, number][] = [];
  for (const w of waypoints) {
    const c = cleanCoordPair(w);
    if (!c) continue;
    if (out.length === 0) {
      out.push(c);
      continue;
    }
    const prev = out[out.length - 1];
    if (haversineKm(prev[0], prev[1], c[0], c[1]) <= maxSeg) out.push(c);
  }
  return out.length >= 2 ? out : out.length === 1 ? out : undefined;
}

/**
 * Validate trajectory start/end; drop end (or both) if chord is impossible for threat type.
 */
export function sanitizeTrajectoryEndpoints(
  start: [number, number] | undefined,
  end: [number, number] | undefined,
  threatType: string,
): { start?: [number, number]; end?: [number, number] } {
  const s = cleanCoordPair(start);
  const e = cleanCoordPair(end);
  const maxChord = maxTrajectoryChordKmForThreat(threatType);
  if (s && e) {
    if (haversineKm(s[0], s[1], e[0], e[1]) > maxChord) {
      return { start: s, end: undefined };
    }
  }
  return { start: s, end: e };
}

/**
 * Sort, dedupe micro-jitter, remove outlier vertices vs implied speed cap (same caps as build-markers).
 */
export function sanitizeTrackPoints(
  points: SanitizeTrackPoint[],
  speedCapKmh: number,
  options?: { burstFactor?: number; minDistKmForSpike?: number },
): SanitizeTrackPoint[] {
  const burst = options?.burstFactor ?? 2.35;
  const minSpike = options?.minDistKmForSpike ?? 2.2;

  const valid = points.filter(
    (p) =>
      Number.isFinite(p.lat) &&
      Number.isFinite(p.lng) &&
      Number.isFinite(p.ts) &&
      p.ts > 0 &&
      isPlausibleThreatCoordinate(p.lat, p.lng),
  );
  if (valid.length === 0) return [];

  valid.sort((a, b) => a.ts - b.ts);

  const deduped: SanitizeTrackPoint[] = [];
  for (const p of valid) {
    const last = deduped[deduped.length - 1];
    if (
      last &&
      Math.abs(last.ts - p.ts) < 450 &&
      haversineKm(last.lat, last.lng, p.lat, p.lng) < 0.035
    ) {
      deduped[deduped.length - 1] = p;
      continue;
    }
    deduped.push(p);
  }

  const cap = Math.max(80, speedCapKmh);
  const kept: SanitizeTrackPoint[] = [deduped[0]];
  for (let i = 1; i < deduped.length; i++) {
    const curr = deduped[i];
    const prev = kept[kept.length - 1];
    const dtMs = curr.ts - prev.ts;
    const distKm = haversineKm(prev.lat, prev.lng, curr.lat, curr.lng);

    if (dtMs <= 0) {
      if (distKm < 0.45) continue;
      kept.push(curr);
      continue;
    }

    if (distKm < 0.018 && dtMs < 950) continue;

    const dtHours = dtMs / 3_600_000;
    const impliedSpeed = distKm / dtHours;

    if (distKm >= minSpike && impliedSpeed > cap * burst) continue;

    if (distKm > 0.85 && impliedSpeed > cap * burst * 1.55) continue;

    kept.push(curr);
  }

  return kept;
}

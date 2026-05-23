import type { AITrajectory, ThreatMarker, ThreatTrackPoint, TrajectoryPoint } from '../../../types/map';

function num(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function int(value: unknown): number | undefined {
  const parsed = num(value);
  return parsed == null ? undefined : Math.trunc(parsed);
}

function str(value: unknown): string | undefined {
  if (value == null) return undefined;
  return String(value);
}

function parseTrajectoryPoint(value: unknown): TrajectoryPoint | null {
  if (!value || typeof value !== 'object') return null;
  const o = value as Record<string, unknown>;
  const lat = num(o.lat);
  const lng = num(o.lng);
  if (lat == null || lng == null) return null;
  return {
    lat,
    lng,
    etaMinutes: num(o.eta_minutes) ?? num(o.etaMinutes) ?? 0,
    fraction: num(o.fraction) ?? 0,
  };
}

function parseAiTrajectory(value: unknown): AITrajectory | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const o = value as Record<string, unknown>;
  const start = Array.isArray(o.start) ? o.start : [];
  const end = Array.isArray(o.end) ? o.end : [];
  const startLat = num(start[0]);
  const startLng = num(start[1]);
  const endLat = num(end[0]);
  const endLng = num(end[1]);
  if ([startLat, startLng, endLat, endLng].some((v) => v == null)) return undefined;
  return {
    startLat: startLat ?? 0,
    startLng: startLng ?? 0,
    endLat: endLat ?? 0,
    endLng: endLng ?? 0,
    sourceName: str(o.source_name) ?? '',
    targetName: str(o.target_name) ?? '',
    predicted: o.predicted === true,
  };
}

function parseTrackPoint(value: unknown): ThreatTrackPoint | null {
  if (!value || typeof value !== 'object') return null;
  const o = value as Record<string, unknown>;
  const lat = num(o.lat);
  const lng = num(o.lng);
  let ts = int(o.ts) ?? 0;
  if (ts > 0 && ts < 20000000000) ts *= 1000;
  if (lat == null || lng == null) return null;
  return { lat, lng, ts };
}

export function isInUkraineOperationalBounds(lat: number, lng: number): boolean {
  return lat >= 43 && lat <= 53.8 && lng >= 20 && lng <= 42.5;
}

export function parseThreatMarker(raw: unknown): ThreatMarker | null {
  if (!raw || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  const lat = num(o.lat);
  const lng = num(o.lng);
  if (lat == null || lng == null || !isInUkraineOperationalBounds(lat, lng)) return null;

  const projectedPath = Array.isArray(o.projected_path)
    ? o.projected_path.map(parseTrajectoryPoint).filter((p): p is TrajectoryPoint => !!p)
    : undefined;
  const positions = Array.isArray(o.positions)
    ? o.positions.map(parseTrackPoint).filter((p): p is ThreatTrackPoint => !!p)
    : undefined;

  return {
    id: str(o.id),
    trackId: str(o.track_id),
    lat,
    lng,
    threatType: str(o.threat_type) ?? 'default',
    place: str(o.place) ?? '',
    text: str(o.text) ?? '',
    date: str(o.date) ?? '',
    projectedPath,
    trajectory: parseAiTrajectory(o.trajectory),
    etaMinutes: num(o.eta_minutes),
    distanceKm: num(o.distance_km),
    count: int(o.count),
    confidence0_100: int(o.confidence_0_100),
    placementMode: str(o.placement_mode),
    confidence: num(o.confidence),
    courseBearing: num(o.course_bearing),
    tickerBearing: num(o.ticker_bearing),
    courseDirection: str(o.course_direction),
    arrowDirection: str(o.arrow_direction),
    positions,
    markerIcon: str(o.marker_icon),
    updatedAt: Date.now(),
  };
}

export function markerKey(marker: Pick<ThreatMarker, 'id' | 'trackId' | 'lat' | 'lng' | 'threatType'>): string {
  return marker.id || marker.trackId || `${marker.threatType}:${marker.lat.toFixed(4)}:${marker.lng.toFixed(4)}`;
}

import type { Marker, Trajectory } from '@/types';

/**
 * Heuristic: if backend put [lon, lat] into [lat, lng] fields, points land
 * in the Black Sea / wrong country for "southern Ukraine" events.
 * Ukraine (rough): lat 43.3–52.4, lon 22.0–40.2
 */
const UKR_LAT_MIN = 43.2;
const UKR_LAT_MAX = 52.6;
const UKR_LNG_MIN = 22.0;
const UKR_LNG_MAX = 40.3;

function looksLikeUkraine(lat: number, lng: number): boolean {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= UKR_LAT_MIN &&
    lat <= UKR_LAT_MAX &&
    lng >= UKR_LNG_MIN &&
    lng <= UKR_LNG_MAX
  );
}

/**
 * Detect classic swapped pair: first value in longitude range, second in latitude range.
 */
function likelyLatLngSwapped(lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (looksLikeUkraine(lat, lng)) return false;
  return (
    lat >= UKR_LNG_MIN &&
    lat <= UKR_LNG_MAX &&
    lng >= UKR_LAT_MIN &&
    lng <= UKR_LAT_MAX
  );
}

/** Returns [lat, lng] in Leaflet order (WGS84). */
export function fixLatLngOrderForUkraine(lat: number, lng: number): [number, number] {
  if (likelyLatLngSwapped(lat, lng)) {
    return [lng, lat];
  }
  return [lat, lng];
}

function fixPair(p: [number, number] | undefined): [number, number] | undefined {
  if (p == null || p.length < 2) return p;
  const [a, b] = p;
  const [la, lo] = fixLatLngOrderForUkraine(a, b);
  return [la, lo];
}

function fixTrajectory(t: Trajectory | null | undefined): Trajectory | null | undefined {
  if (t == null) return t;
  const next: Trajectory = { ...t };
  if (t.start) next.start = fixPair(t.start);
  if (t.end) next.end = fixPair(t.end);
  if (t.origin_coords) next.origin_coords = fixPair(t.origin_coords);
  if (t.waypoints?.length) {
    next.waypoints = t.waypoints.map((w) => fixPair(w)!) as [number, number][];
  }
  return next;
}

/**
 * Apply coordinate-order fix to marker and nested path fields (for map display).
 */
export function normalizeMarkerGeocoords(m: Marker): Marker {
  const rawLat = Number(m.lat);
  const rawLng = Number(m.lng);
  if (!Number.isFinite(rawLat) || !Number.isFinite(rawLng)) return m;

  const [lat, lng] = fixLatLngOrderForUkraine(rawLat, rawLng);
  const out: Marker = { ...m, lat, lng };

  if (m.trajectory) {
    out.trajectory = fixTrajectory(m.trajectory) ?? m.trajectory;
  }
  if (m.positions?.length) {
    out.positions = m.positions.map((p) => {
      const [pl, pLo] = fixLatLngOrderForUkraine(p.lat, p.lng);
      return { ...p, lat: pl, lng: pLo };
    });
  }
  if (m.observations?.length) {
    out.observations = m.observations.map((o) => {
      const [ol, oLo] = fixLatLngOrderForUkraine(o.lat, o.lng);
      return { ...o, lat: ol, lng: oLo };
    });
  }
  return out;
}

export function normalizeMarkersGeocoords(markers: Marker[]): Marker[] {
  return markers.map(normalizeMarkerGeocoords);
}

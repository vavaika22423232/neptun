/**
 * Plausible coordinate box for Ukrainian threat map (+ Black Sea margin).
 * Keep in sync with `worker/geo_bounds.py` (ingest pipeline + web filter).
 */
export const UKRAINE_THREAT_BOUNDS = {
  minLat: 42.5,
  maxLat: 53.5,
  minLng: 20.0,
  maxLng: 41.5,
} as const;

export type PlausibleCoordOptions = {
  /** Manual / admin markers may sit slightly outside the box; still reject NaN and null-island. */
  allowOutsideThreatRegion?: boolean;
};

export function isPlausibleThreatCoordinate(
  lat: number,
  lng: number,
  options?: PlausibleCoordOptions,
): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (Math.abs(lat) < 0.5 && Math.abs(lng) < 0.5) return false;
  if (options?.allowOutsideThreatRegion) return true;
  return (
    lat >= UKRAINE_THREAT_BOUNDS.minLat &&
    lat <= UKRAINE_THREAT_BOUNDS.maxLat &&
    lng >= UKRAINE_THREAT_BOUNDS.minLng &&
    lng <= UKRAINE_THREAT_BOUNDS.maxLng
  );
}

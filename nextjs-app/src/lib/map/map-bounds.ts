/**
 * Single authoritative MAP_BOUNDS constant for all GeoJSON builders and map utilities.
 * Import from here — do not redeclare inline in individual files.
 */
export const MAP_BOUNDS = {
  minLat: 44.2,
  maxLat: 52.4,
  minLng: 22.0,
  maxLng: 40.2,
} as const;

export function inMapBounds(lat: number, lng: number): boolean {
  return (
    lat >= MAP_BOUNDS.minLat &&
    lat <= MAP_BOUNDS.maxLat &&
    lng >= MAP_BOUNDS.minLng &&
    lng <= MAP_BOUNDS.maxLng
  );
}

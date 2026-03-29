import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';

/**
 * Reject garbage coordinates before they hit Redis / spatial correlator.
 * Worker should apply the same rules (`worker/geo_bounds.py`).
 */
export function validateIngestMarker(marker: Record<string, unknown>): { ok: true } | { ok: false; error: string } {
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { ok: false, error: 'Invalid lat/lng' };
  }
  const manual = Boolean(marker.manual);
  if (!isPlausibleThreatCoordinate(lat, lng, { allowOutsideThreatRegion: manual })) {
    return { ok: false, error: 'Coordinates outside allowed region' };
  }
  return { ok: true };
}

/** PATCH may only send partial fields — validate if lat/lng are being changed. */
export function validateIngestPatchUpdates(updates: Record<string, unknown>): { ok: true } | { ok: false; error: string } {
  const hasLat = 'lat' in updates;
  const hasLng = 'lng' in updates;
  if (!hasLat && !hasLng) return { ok: true };
  if (hasLat !== hasLng) {
    return { ok: false, error: 'lat and lng must be updated together' };
  }
  const lat = Number(updates.lat);
  const lng = Number(updates.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { ok: false, error: 'Invalid lat/lng in patch' };
  }
  if (!isPlausibleThreatCoordinate(lat, lng)) {
    return { ok: false, error: 'Coordinates outside allowed region' };
  }
  return { ok: true };
}

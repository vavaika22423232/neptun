import type { ThreatMarker } from '../../../types/map';
import { haversineKm } from '../utils/haversine';
import { markerKey } from '../utils/parseThreatMarker';
import { markerMotionEngine } from './markerMotionEngine';

function motionDurationMs(prev: ThreatMarker, next: ThreatMarker): number {
  const km = haversineKm(prev.lat, prev.lng, next.lat, next.lng);
  return Math.min(900, Math.max(140, Math.round(km * 120 + 180)));
}

/**
 * Schedule eased motion after SSE `track_update` (native MapLibre path only).
 */
export function scheduleMarkerMotion(prev: ThreatMarker, next: ThreatMarker): void {
  if (prev.lat === next.lat && prev.lng === next.lng) return;
  const key = markerKey(next);
  const bearing = next.courseBearing ?? next.tickerBearing;
  markerMotionEngine.schedule(
    key,
    { lat: prev.lat, lng: prev.lng },
    { lat: next.lat, lng: next.lng },
    bearing,
    motionDurationMs(prev, next),
  );
}

export function cancelMarkerMotion(key: string): void {
  markerMotionEngine.cancel(key);
}

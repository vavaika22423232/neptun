import type { ThreatMarker } from '../../../types/map';
import type { MotionCoord } from '../engine/markerMotionEngine';
import { markerKey } from './parseThreatMarker';

export function mergeMotionIntoMarkers(
  markers: ThreatMarker[],
  motion: Map<string, MotionCoord>,
): ThreatMarker[] {
  if (motion.size === 0) return markers;
  return markers.map((m) => {
    const key = markerKey(m);
    const pos = motion.get(key);
    if (!pos) return m;
    return { ...m, lat: pos.lat, lng: pos.lng };
  });
}

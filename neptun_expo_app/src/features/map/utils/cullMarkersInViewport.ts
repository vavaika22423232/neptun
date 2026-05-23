import type { ThreatMarker } from '../../../types/map';
import type { MapViewportBounds } from './viewportBounds';

const PAD_RATIO = 0.12;

export function cullMarkersInViewport(
  markers: ThreatMarker[],
  bounds: MapViewportBounds | null,
): ThreatMarker[] {
  if (!bounds) return markers;
  const latSpan = bounds.north - bounds.south;
  const lngSpan = bounds.east - bounds.west;
  const latPad = latSpan * PAD_RATIO;
  const lngPad = lngSpan * PAD_RATIO;
  const north = bounds.north + latPad;
  const south = bounds.south - latPad;
  const east = bounds.east + lngPad;
  const west = bounds.west - lngPad;

  return markers.filter((m) => m.lat >= south && m.lat <= north && m.lng >= west && m.lng <= east);
}

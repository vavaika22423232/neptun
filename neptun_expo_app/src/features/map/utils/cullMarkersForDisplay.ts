import type { ThreatMarker } from '../../../types/map';
import { cullMarkersInViewport } from './cullMarkersInViewport';
import type { MapViewportBounds } from './viewportBounds';

const DEFAULT_MAX = 2000;

export type MarkerCullOptions = {
  max?: number;
  viewport?: MapViewportBounds | null;
};

/**
 * Viewport filter + newest-N cap (Flutter map culling analogue).
 */
export function cullMarkersForDisplay(markers: ThreatMarker[], options?: MarkerCullOptions | number): ThreatMarker[] {
  const opts: MarkerCullOptions =
    typeof options === 'number' ? { max: options } : (options ?? {});
  const max = opts.max ?? DEFAULT_MAX;
  let out = cullMarkersInViewport(markers, opts.viewport ?? null);
  if (out.length <= max) return out;
  return [...out]
    .sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0))
    .slice(0, max);
}

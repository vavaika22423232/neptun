/** Visible map bounds (WGS84). Mirrors Flutter map viewport culling inputs. */
export type MapViewportBounds = {
  north: number;
  south: number;
  east: number;
  west: number;
};

/** @rnmapbox/maps `visibleBounds`: [[neLng, neLat], [swLng, swLat]] */
export function boundsFromMapboxVisible(visibleBounds: number[][] | undefined): MapViewportBounds | null {
  if (!visibleBounds || visibleBounds.length < 2) return null;
  const ne = visibleBounds[0];
  const sw = visibleBounds[1];
  if (!ne || !sw || ne.length < 2 || sw.length < 2) return null;
  const [neLng, neLat] = ne;
  const [swLng, swLat] = sw;
  if (![neLng, neLat, swLng, swLat].every((n) => Number.isFinite(n))) return null;
  return {
    north: Math.max(neLat, swLat),
    south: Math.min(neLat, swLat),
    east: Math.max(neLng, swLng),
    west: Math.min(neLng, swLng),
  };
}

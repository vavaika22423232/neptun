import type { FeatureCollection, Polygon } from 'geojson';
/** Дублікат `public/geoBoundaries-UKR-ADM0_simplified.geojson` (розширення .json — імпорт у Turbopack). Оновлювати обидва файли разом. */
import raw from './ukraine-adm0-simplified.json';

function loadOuterRingLngLat(): readonly [number, number][] {
  const fc = raw as FeatureCollection;
  const geom = fc.features[0]?.geometry as Polygon | undefined;
  const rings = geom?.coordinates;
  const outer = rings?.[0];
  if (!outer || outer.length < 4) {
    throw new Error('geoBoundaries-UKR-ADM0_simplified: missing outer ring');
  }
  return outer as [number, number][];
}

/** GeoJSON outer ring [lng, lat] — один раз при завантаженні модуля. */
const OUTER_RING_LNG_LAT = loadOuterRingLngLat();

/**
 * Точка всередині спрощеного адмінконтуру України (CRS84, lng/lat як у GeoJSON).
 * Використовується, щоб «ройові» піни не з’їжджали в сусідні країни біля кордону (напр. Рені).
 */
export function isLngLatInsideUkraineAdm0(lng: number, lat: number): boolean {
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return false;
  return pointInPolygonLngLat(lng, lat, OUTER_RING_LNG_LAT);
}

function pointInPolygonLngLat(lng: number, lat: number, ring: readonly [number, number][]): boolean {
  let inside = false;
  const n = ring.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const denom = yj - yi;
    if (denom === 0) continue;
    if ((yi > lat) === (yj > lat)) continue;
    const xInt = ((xj - xi) * (lat - yi)) / denom + xi;
    if (lng < xInt) inside = !inside;
  }
  return inside;
}

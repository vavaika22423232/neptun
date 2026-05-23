import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson';
import type { MapAlarmData } from '../../../types/map';
// eslint-disable-next-line @typescript-eslint/no-require-imports
// Bundled from src. Run `npm run sync:map-geo` after editing assets/geo/ukraine_districts.geojson
const DISTRICTS_RAW = require('../data/ukraine_districts.json') as FeatureCollection;

/** Flutter `SvgMapPainter` dark district alarm fill: rgb(185, 28, 28) @ 0.7 */
export const DISTRICT_ALARM_FILL = 'rgba(185,28,28,0.55)';

let cachedBase: FeatureCollection | null = null;

function baseDistrictCollection(): FeatureCollection {
  if (cachedBase) return cachedBase;
  const features: Feature[] = [];
  for (const raw of DISTRICTS_RAW.features ?? []) {
    const regionId = String((raw.properties as Record<string, unknown>)?.regionId ?? '');
    if (!regionId) continue;
    const geom = raw.geometry;
    if (geom?.type !== 'Polygon' && geom?.type !== 'MultiPolygon') continue;
    features.push({
      type: 'Feature',
      geometry: geom as Polygon | MultiPolygon,
      properties: {
        regionId,
        hasAlarm: false,
      },
    });
  }
  cachedBase = { type: 'FeatureCollection', features };
  return cachedBase;
}

/** District polygons with active air alarm only (Flutter draws alarmed districts). */
export function buildDistrictAlarmGeoJson(alarms: MapAlarmData): FeatureCollection {
  const base = baseDistrictCollection();
  const features: Feature[] = [];
  for (const f of base.features) {
    const regionId = String(f.properties?.regionId ?? '');
    if (!alarms.districtAlarms[regionId]) continue;
    features.push({
      ...f,
      properties: {
        ...f.properties,
        regionId,
        hasAlarm: true,
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

/** All district outlines — visible from zoom ≥ 7.5 (Flutter `_distBorder`). */
export function buildDistrictBorderGeoJson(): FeatureCollection {
  return baseDistrictCollection();
}

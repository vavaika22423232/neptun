import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson';
import type { MapAlarmData, ThreatType } from '../../../types/map';
import { HASC_TO_STATE_ID } from '../constants/hascToStateId';
// eslint-disable-next-line @typescript-eslint/no-require-imports
// Bundled from src (Metro does not follow symlinks under /assets). Source: assets/geo/ukraine_oblasts.geojson
const OBLASTS_RAW = require('../data/ukraine_oblasts.json') as FeatureCollection;

let cachedBase: FeatureCollection | null = null;

function baseOblastCollection(): FeatureCollection {
  if (cachedBase) return cachedBase;
  const features: Feature[] = [];
  for (const raw of OBLASTS_RAW.features ?? []) {
    const hasc = String((raw.properties as Record<string, unknown>)?.HASC_1 ?? '');
    const stateId = HASC_TO_STATE_ID[hasc];
    if (!stateId) continue;
    const geom = raw.geometry;
    if (geom?.type !== 'Polygon' && geom?.type !== 'MultiPolygon') continue;
    features.push({
      type: 'Feature',
      geometry: geom as Polygon | MultiPolygon,
      properties: {
        stateId,
        hasAlarm: false,
        threatType: '',
      },
    });
  }
  cachedBase = { type: 'FeatureCollection', features };
  return cachedBase;
}

export function buildOblastAlarmGeoJson(alarms: MapAlarmData): FeatureCollection {
  const base = baseOblastCollection();
  return {
    type: 'FeatureCollection',
    features: base.features.map((f) => {
      const stateId = String(f.properties?.stateId ?? '');
      const hasAlarm = !!alarms.stateAlarms[stateId];
      const threatType = (alarms.stateThreatTypes[stateId] ?? '') as ThreatType | '';
      return {
        ...f,
        properties: {
          ...f.properties,
          hasAlarm,
          threatType: hasAlarm ? String(threatType || 'alarm') : '',
        },
      };
    }),
  };
}

import type { Feature, FeatureCollection, Polygon, Position } from 'geojson';
import { HASC_TO_STATE_ID } from '../../map/constants/hascToStateId';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const OBLASTS_RAW = require('../../map/data/ukraine_oblasts.json') as FeatureCollection;

let cached: Record<string, [number, number]> | null = null;

function ringCentroid(ring: Position[]): [number, number] {
  let sumLat = 0;
  let sumLng = 0;
  let n = 0;
  for (const p of ring) {
    if (p.length < 2) continue;
    sumLng += p[0];
    sumLat += p[1];
    n += 1;
  }
  if (n === 0) return [31.5, 48.5];
  return [sumLng / n, sumLat / n];
}

function featureCentroid(f: Feature): [number, number] | null {
  const g = f.geometry;
  if (!g) return null;
  if (g.type === 'Polygon') {
    const ring = (g as Polygon).coordinates[0];
    return ring ? ringCentroid(ring) : null;
  }
  if (g.type === 'MultiPolygon') {
    const ring = g.coordinates[0]?.[0];
    return ring ? ringCentroid(ring) : null;
  }
  return null;
}

/** `[lng, lat]` per heatmap state id `1`…`27`. */
export function getOblastCentroidsByStateId(): Record<string, [number, number]> {
  if (cached) return cached;
  const map: Record<string, [number, number]> = {};
  for (const raw of OBLASTS_RAW.features ?? []) {
    const hasc = String((raw.properties as Record<string, unknown>)?.HASC_1 ?? '');
    const stateId = HASC_TO_STATE_ID[hasc];
    if (!stateId) continue;
    const c = featureCentroid(raw as Feature);
    if (c) map[stateId] = c;
  }
  cached = map;
  return map;
}

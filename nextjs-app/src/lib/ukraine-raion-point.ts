/**
 * Point-in-polygon for `public/ukraine_raions_2020.geojson` — rayon name at (lat,lng).
 */

import fs from 'fs';
import path from 'path';

type Ring = [number, number][];

type RayonIndexEntry = { rayonNorm: string; rings: Ring[] };

let cachedEntries: RayonIndexEntry[] | null = null;

function ringsFromGeometry(geom: {
  type: string;
  coordinates: unknown;
}): Ring[] {
  const out: Ring[] = [];
  if (geom.type === 'Polygon') {
    const coords = geom.coordinates as Ring[];
    if (coords[0]) out.push(coords[0] as Ring);
    return out;
  }
  if (geom.type === 'MultiPolygon') {
    const multi = geom.coordinates as number[][][][];
    for (const poly of multi) {
      const outer = poly[0];
      if (outer) out.push(outer as Ring);
    }
  }
  return out;
}

function pointInRing(lng: number, lat: number, ring: Ring): boolean {
  if (ring.length < 3) return false;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const denom = yj - yi;
    if (denom === 0) continue;
    const intersect =
      (yi > lat) !== (yj > lat) &&
      lng < ((xj - xi) * (lat - yi)) / denom + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function buildIndex(): RayonIndexEntry[] {
  const file = path.join(process.cwd(), 'public', 'ukraine_raions_2020.geojson');
  const raw = fs.readFileSync(file, 'utf-8');
  const gj = JSON.parse(raw) as {
    features: Array<{
      properties?: { rayon?: string } | null;
      geometry: { type: string; coordinates: unknown };
    }>;
  };
  const out: RayonIndexEntry[] = [];
  for (const f of gj.features || []) {
    const r = String(f.properties?.rayon || '').trim();
    if (!r) continue;
    const rings = ringsFromGeometry(f.geometry);
    if (!rings.length) continue;
    const rayonNorm = r
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{M}/gu, '')
      .replace(/['ʼ`]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    if (!rayonNorm) continue;
    out.push({ rayonNorm, rings });
  }
  return out;
}

function getEntries(): RayonIndexEntry[] {
  if (!cachedEntries) cachedEntries = buildIndex();
  return cachedEntries;
}

/** Нормалізована назва району (`rayon`), що містить точку, або null. */
export function findRayonNormalizedContainingPoint(lat: number, lng: number): string | null {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  for (const { rayonNorm, rings } of getEntries()) {
    for (const ring of rings) {
      if (pointInRing(lng, lat, ring)) return rayonNorm;
    }
  }
  return null;
}

/**
 * Point-in-polygon for `public/ukraine_oblasts.geojson` — oblast label + HASC at (lat,lng).
 */

import fs from 'fs';
import path from 'path';

type Ring = [number, number][];

type OblastIndexEntry = {
  nameUk: string;
  hasc: string;
  rings: Ring[];
};

let cachedEntries: OblastIndexEntry[] | null = null;

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

function buildIndex(): OblastIndexEntry[] {
  const file = path.join(process.cwd(), 'public', 'ukraine_oblasts.geojson');
  const raw = fs.readFileSync(file, 'utf-8');
  const gj = JSON.parse(raw) as {
    features: Array<{
      properties?: Record<string, unknown> | null;
      geometry: { type: string; coordinates: unknown };
    }>;
  };
  const out: OblastIndexEntry[] = [];
  for (const f of gj.features || []) {
    const p = f.properties;
    if (!p) continue;
    const hasc = String(p.HASC_1 || '').trim();
    if (!hasc || hasc === '?') continue;
    const nameUk = String(p.NL_NAME_1 || p.NAME_1 || '').trim();
    if (!nameUk) continue;
    const rings = ringsFromGeometry(f.geometry);
    if (!rings.length) continue;
    out.push({ nameUk, hasc, rings });
  }
  return out;
}

function getEntries(): OblastIndexEntry[] {
  if (!cachedEntries) cachedEntries = buildIndex();
  return cachedEntries;
}

export type OblastAtPoint = {
  nameUk: string;
  hasc: string;
};

/** Oblast containing (lat,lng), or null if outside indexed polygons. */
export function findOblastAtPoint(lat: number, lng: number): OblastAtPoint | null {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  for (const entry of getEntries()) {
    for (const ring of entry.rings) {
      if (pointInRing(lng, lat, ring)) {
        return { nameUk: entry.nameUk, hasc: entry.hasc };
      }
    }
  }
  return null;
}

/** Short subtitle line for search UI (oblast + optional raion). */
export function formatPlaceSubtitle(oblastLabel: string, raion?: string | null): string {
  const parts: string[] = [];
  if (oblastLabel) {
    parts.push(oblastLabel.replace(/ область$/i, ' обл.'));
  }
  if (raion) parts.push(`${raion} р-н`);
  return parts.join(', ') || 'Україна';
}

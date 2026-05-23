import fs from 'fs';
import path from 'path';
import type { PlaceSearchResult } from '@/lib/places-search/types';
import { placeTypeFromGeojson } from '@/lib/places-search/place-type';
import {
  compactPlaceQuery,
  expandPlaceQueryAliases,
  normalizePlaceQuery,
} from '@/lib/places-search/normalize-query';
import { findOblastAtPoint, formatPlaceSubtitle } from '@/lib/places-search/ukraine-oblast-point';

type GeoRow = {
  name: string;
  nameLower: string;
  nameCompact: string;
  lat: number;
  lng: number;
  placeType: string;
  population: number;
};

let index: GeoRow[] | null = null;
let loadFailed = false;

function geojsonPath(): string {
  return path.join(process.cwd(), 'public', 'ukraine_settlements.geojson');
}

function loadIndex(): GeoRow[] {
  if (index) return index;
  if (loadFailed) return [];
  const fp = geojsonPath();
  if (!fs.existsSync(fp)) {
    loadFailed = true;
    return [];
  }
  try {
    const raw = JSON.parse(fs.readFileSync(fp, 'utf-8')) as {
      features?: Array<{
        geometry?: { coordinates?: [number, number] };
        properties?: { n?: string; c?: string; p?: number };
      }>;
    };
    const rows: GeoRow[] = [];
    for (const f of raw.features ?? []) {
      const name = String(f.properties?.n ?? '').trim();
      const coords = f.geometry?.coordinates;
      if (!name || !coords || coords.length < 2) continue;
      const [lng, lat] = coords;
      rows.push({
        name,
        nameLower: name.toLowerCase(),
        nameCompact: compactPlaceQuery(name),
        lat,
        lng,
        placeType: String(f.properties?.c ?? ''),
        population: Number(f.properties?.p ?? 0) || 0,
      });
    }
    index = rows;
    return rows;
  } catch {
    loadFailed = true;
    return [];
  }
}

function scoreRow(row: GeoRow, q: string): number {
  const qc = compactPlaceQuery(q);
  if (row.nameLower === q || row.nameCompact === qc) return 0;
  if (row.nameLower.startsWith(q) || row.nameCompact.startsWith(qc)) return 1;
  if (row.nameLower.includes(q) || row.nameCompact.includes(qc)) return 2;
  return 99;
}

export function searchGeojsonPlaces(
  query: string,
  limit: number,
  typeFilter?: string,
): PlaceSearchResult[] {
  const queries = expandPlaceQueryAliases(normalizePlaceQuery(query));
  if (!queries[0] || queries[0].length < 2) return [];

  const rows = loadIndex();
  if (!rows.length) return [];

  const scored: Array<{ row: GeoRow; score: number }> = [];
  for (const row of rows) {
    let best = 99;
    for (const q of queries) {
      const s = scoreRow(row, q);
      if (s < best) best = s;
    }
    if (best >= 99) continue;
    const pt = placeTypeFromGeojson(row.placeType);
    if (typeFilter && pt !== typeFilter) continue;
    scored.push({ row, score: best });
  }

  scored.sort((a, b) => {
    if (a.score !== b.score) return a.score - b.score;
    return b.row.population - a.row.population;
  });

  const seen = new Set<string>();
  const out: PlaceSearchResult[] = [];
  for (const { row, score } of scored) {
    const key = `${row.nameLower}|${row.lat.toFixed(3)}|${row.lng.toFixed(3)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const pt = placeTypeFromGeojson(row.placeType);
    const oblast = findOblastAtPoint(row.lat, row.lng);
    out.push({
      id: `geojson:${row.nameLower}:${row.lat.toFixed(4)}:${row.lng.toFixed(4)}`,
      name: row.name,
      nameUk: row.name,
      subtitle: oblast
        ? formatPlaceSubtitle(oblast.nameUk)
        : 'Україна',
      placeType: pt,
      lat: row.lat,
      lng: row.lng,
      oblastHasc: oblast?.hasc,
      population: row.population || undefined,
      source: 'geojson',
    });
    if (out.length >= limit) break;
    void score;
  }
  return out;
}

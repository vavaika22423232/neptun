import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';
import type { PlaceSearchResult } from '@/lib/places-search/types';
import { citySlugForName, regionSlugForCitySlug } from '@/lib/places-search/city-slugs';
import {
  compactPlaceQuery,
  expandPlaceQueryAliases,
  normalizePlaceQuery,
} from '@/lib/places-search/normalize-query';
import { resolveOblastHasc } from '@/lib/places-search/oblast-hasc';
import { placeTypeFromGazetteer } from '@/lib/places-search/place-type';
import { searchGeojsonPlaces } from '@/lib/places-search/geojson-index';
import { formatPlaceSubtitle } from '@/lib/places-search/ukraine-oblast-point';

const DATA_DIR = process.env.DATA_DIR || '/data';
const DB_PATH = path.join(DATA_DIR, 'settlements.db');
const FALLBACK_DB = path.resolve(process.cwd(), 'worker', 'geo', 'data', 'settlements.db');

let db: Database.Database | null = null;
let ftsAvailable: boolean | null = null;

export function getSettlementsDbPath(): string {
  if (fs.existsSync(DB_PATH)) return DB_PATH;
  if (fs.existsSync(FALLBACK_DB)) return FALLBACK_DB;
  return DB_PATH;
}

export function isSettlementsDbAvailable(): boolean {
  return fs.existsSync(getSettlementsDbPath());
}

function getDb(): Database.Database {
  if (!db) {
    const fp = getSettlementsDbPath();
    if (!fs.existsSync(fp)) {
      throw new Error(`settlements.db not found at ${fp}`);
    }
    db = new Database(fp, { readonly: true, fileMustExist: true });
  }
  return db;
}

function hasFtsTable(conn: Database.Database): boolean {
  if (ftsAvailable !== null) return ftsAvailable;
  const row = conn
    .prepare(
      "SELECT 1 FROM sqlite_master WHERE type='table' AND name='places_fts' LIMIT 1",
    )
    .get();
  ftsAvailable = Boolean(row);
  return ftsAvailable;
}

type RawRow = {
  id: number;
  name: string;
  oblast: string;
  raion: string | null;
  lat: number;
  lng: number;
  place_type: string | null;
  population: number;
  match_rank: number;
};

/** Strip ASCII apostrophe so «камянське» matches «кам'янське» (query side strips more). */
function sqlCompactExpr(column: string): string {
  return `REPLACE(${column}, '''', '')`;
}

function searchGazetteerSql(
  conn: Database.Database,
  queries: string[],
  limit: number,
  typeFilter?: string,
): RawRow[] {
  const allRows = new Map<number, RawRow>();
  const nameCompact = sqlCompactExpr('p.name_lower');
  const aliasCompact = sqlCompactExpr('a.alias');

  for (const q of queries) {
    const prefix = `${q}%`;
    const contains = `%${q}%`;
    const qc = compactPlaceQuery(q);

    const baseSelect = `
      SELECT p.id, p.name, p.oblast, p.raion, p.lat, p.lng, p.place_type, p.population,
        CASE
          WHEN p.name_lower = @q OR ${nameCompact} = @qc THEN 0
          WHEN p.name_lower LIKE @prefix OR ${nameCompact} LIKE @prefix THEN 1
          ELSE 2
        END AS match_rank
      FROM places p
      WHERE p.name_lower = @q OR p.name_lower LIKE @prefix OR p.name_lower LIKE @contains
         OR ${nameCompact} = @qc OR ${nameCompact} LIKE @prefix OR ${nameCompact} LIKE @contains
    `;

    const aliasSelect = `
      SELECT p.id, p.name, p.oblast, p.raion, p.lat, p.lng, p.place_type, p.population,
        CASE
          WHEN a.alias = @q OR ${aliasCompact} = @qc THEN 1
          WHEN a.alias LIKE @prefix OR ${aliasCompact} LIKE @prefix THEN 2
          ELSE 3
        END AS match_rank
      FROM aliases a
      JOIN places p ON p.id = a.canonical_id
      WHERE a.alias = @q OR a.alias LIKE @prefix OR a.alias LIKE @contains
         OR ${aliasCompact} = @qc OR ${aliasCompact} LIKE @prefix OR ${aliasCompact} LIKE @contains
    `;

    const params = { q, qc, prefix, contains };
    for (const row of conn.prepare(baseSelect).all(params) as RawRow[]) {
      const prev = allRows.get(row.id);
      if (!prev || row.match_rank < prev.match_rank) allRows.set(row.id, row);
    }
    for (const row of conn.prepare(aliasSelect).all(params) as RawRow[]) {
      const prev = allRows.get(row.id);
      if (!prev || row.match_rank < prev.match_rank) allRows.set(row.id, row);
    }

    if (hasFtsTable(conn)) {
      const ftsQ = queries.map((x) => `"${x.replace(/"/g, '')}"`).join(' OR ');
      try {
        const ftsSelect = `
          SELECT p.id, p.name, p.oblast, p.raion, p.lat, p.lng, p.place_type, p.population, 2 AS match_rank
          FROM places_fts f
          JOIN places p ON p.id = f.rowid
          WHERE f MATCH @fts
        `;
        for (const row of conn.prepare(ftsSelect).all({ fts: ftsQ }) as RawRow[]) {
          const prev = allRows.get(row.id);
          if (!prev) allRows.set(row.id, row);
        }
      } catch {
        /* FTS query syntax — ignore */
      }
    }
  }

  let rows = [...allRows.values()];
  if (typeFilter) {
    rows = rows.filter((r) => placeTypeFromGazetteer(r.place_type) === typeFilter);
  }
  rows.sort((a, b) => {
    if (a.match_rank !== b.match_rank) return a.match_rank - b.match_rank;
    return (b.population || 0) - (a.population || 0);
  });
  return rows.slice(0, limit);
}

function rowToResult(row: RawRow): PlaceSearchResult {
  const pt = placeTypeFromGazetteer(row.place_type);
  const slug = citySlugForName(row.name);
  return {
    id: `gazetteer:${row.id}`,
    name: row.name,
    nameUk: row.name,
    subtitle: formatPlaceSubtitle(row.oblast, row.raion),
    placeType: pt,
    lat: row.lat,
    lng: row.lng,
    oblastHasc: resolveOblastHasc(row.oblast),
    population: row.population || undefined,
    slug,
    regionSlug: slug ? regionSlugForCitySlug(slug) : undefined,
    source: 'gazetteer',
  };
}

function mergeResults(
  primary: PlaceSearchResult[],
  secondary: PlaceSearchResult[],
  limit: number,
): PlaceSearchResult[] {
  const gazetteerNames = new Set(
    primary.map((r) => compactPlaceQuery(r.name)),
  );
  const seen = new Set<string>();
  const out: PlaceSearchResult[] = [];
  for (const r of primary) {
    const key = `${compactPlaceQuery(r.name)}|${r.lat.toFixed(3)}|${r.lng.toFixed(3)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(r);
    if (out.length >= limit) break;
  }
  for (const r of secondary) {
    if (gazetteerNames.has(compactPlaceQuery(r.name))) continue;
    const key = `${compactPlaceQuery(r.name)}|${r.lat.toFixed(3)}|${r.lng.toFixed(3)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(r);
    if (out.length >= limit) break;
  }
  return out;
}

export function searchPlaces(
  rawQuery: string,
  limit: number,
  typeFilter?: string,
): PlaceSearchResult[] {
  const q = normalizePlaceQuery(rawQuery);
  if (q.length < 2) return [];

  const queries = expandPlaceQueryAliases(q);
  const cap = Math.max(1, Math.min(20, limit));

  let gazetteer: PlaceSearchResult[] = [];
  if (isSettlementsDbAvailable()) {
    try {
      const conn = getDb();
      gazetteer = searchGazetteerSql(conn, queries, cap, typeFilter).map(rowToResult);
    } catch (err) {
      console.error('[places-search] gazetteer error:', err);
    }
  }

  if (gazetteer.length >= cap) return gazetteer;

  const geo = searchGeojsonPlaces(rawQuery, cap - gazetteer.length, typeFilter);
  return mergeResults(gazetteer, geo, cap);
}

/** Curated quick picks when the search field is focused with empty query. */
export const POPULAR_PLACE_QUERIES = ['Київ', 'Харків', 'Одеса', 'Дніпро', 'Львів'];

export function popularPlaces(): PlaceSearchResult[] {
  const out: PlaceSearchResult[] = [];
  for (const name of POPULAR_PLACE_QUERIES) {
    const hits = searchPlaces(name, 1);
    if (hits[0]) out.push(hits[0]);
  }
  return out;
}

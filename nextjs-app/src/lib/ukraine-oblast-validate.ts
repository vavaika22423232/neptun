/**
 * Oblast-level consistency: compare worker-stated region fields to coordinates using
 * GADM polygons (`public/ukraine_oblasts.geojson`). On mismatch, snap to the stated oblast
 * centroid and downgrade placement metadata — reduces pins that landed in the wrong
 * oblast due to geocoder homonyms.
 *
 * **Worker-side (recommended, not implemented here):** (1) NER for oblast / direction;
 * (2) geocode micro-places inside a bbox or admin area from step 1; (3) keep `candidates` for
 * low-confidence cases; (4) send `resolved_oblast_hasc` whenever possible so matching does not
 * depend on regex of `region` alone.
 */

import fs from 'fs';
import path from 'path';

export type OblastCentroid = { lat: number; lng: number };

type Ring = [number, number][];

type OblastIndex = {
  hascSet: Set<string>;
  /** Exterior rings only (GeoJSON [lng, lat]); one oblast may have many rings (islands). */
  ringsByHasc: Map<string, Ring[]>;
  centroids: Record<string, OblastCentroid>;
};

let cachedIndex: OblastIndex | null = null;

function geojsonPath(): string {
  return path.join(process.cwd(), 'public', 'ukraine_oblasts.geojson');
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

function pointInAnyRing(lng: number, lat: number, rings: Ring[]): boolean {
  for (const ring of rings) {
    if (pointInRing(lng, lat, ring)) return true;
  }
  return false;
}

function centroidOfRings(rings: Ring[]): OblastCentroid {
  let sumLat = 0;
  let sumLng = 0;
  let n = 0;
  for (const ring of rings) {
    for (const p of ring) {
      sumLng += p[0];
      sumLat += p[1];
      n += 1;
    }
  }
  if (n === 0) return { lat: 48.5, lng: 31.5 };
  return { lat: sumLat / n, lng: sumLng / n };
}

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

function buildIndex(): OblastIndex {
  const raw = fs.readFileSync(geojsonPath(), 'utf-8');
  const gj = JSON.parse(raw) as {
    features: Array<{ properties: { HASC_1?: string }; geometry: { type: string; coordinates: unknown } }>;
  };
  const hascSet = new Set<string>();
  const ringsByHasc = new Map<string, Ring[]>();
  const centroids: Record<string, OblastCentroid> = {};

  for (const f of gj.features || []) {
    const hasc = f.properties?.HASC_1;
    if (!hasc || hasc === '?') continue;
    hascSet.add(hasc);
    const rings = ringsFromGeometry(f.geometry);
    if (!rings.length) continue;
    const prev = ringsByHasc.get(hasc) || [];
    ringsByHasc.set(hasc, prev.concat(rings));
  }

  for (const hasc of hascSet) {
    const rings = ringsByHasc.get(hasc);
    if (rings?.length) {
      centroids[hasc] = centroidOfRings(rings);
    }
  }

  return { hascSet, ringsByHasc, centroids };
}

export function getOblastIndex(): OblastIndex {
  if (!cachedIndex) {
    cachedIndex = buildIndex();
  }
  return cachedIndex;
}

/** Which GADM oblast (HASC_1) contains this point, or null if outside all polygons. */
export function findHascContainingPoint(lat: number, lng: number): string | null {
  const idx = getOblastIndex();
  for (const hasc of idx.hascSet) {
    const rings = idx.ringsByHasc.get(hasc);
    if (rings && pointInAnyRing(lng, lat, rings)) return hasc;
  }
  return null;
}

/** True if (lat,lng) lies inside the GADM polygon for the given HASC_1 (e.g. UA.KK). */
export function isLatLngInOblastHasc(hasc: string, lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  const idx = getOblastIndex();
  const h = hasc.trim().toUpperCase();
  if (!idx.hascSet.has(h)) return false;
  const rings = idx.ringsByHasc.get(h);
  return Boolean(rings?.length && pointInAnyRing(lng, lat, rings));
}

function normalizeRegionText(s: string): string {
  return s
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Map free-text region/oblast strings (UK/RU/Latin) to GADM HASC_1.
 * Order matters: more specific patterns first (city vs oblast, etc.).
 */
const TEXT_TO_HASC: { hasc: string; re: RegExp }[] = [
  { hasc: 'UA.KC', re: /\bм\.?\s*київ\b|київ\s+міст|kyiv\s+city|kievcity|kyiv\s+міст/i },
  { hasc: 'UA.KV', re: /київськ|киевск|kyivska|kievska|київщин|киевщин|kyiv\s+oblast|kiev\s+oblast|київська\s+обл/i },
  { hasc: 'UA.SC', re: /севастопол|sevastopol/i },
  { hasc: 'UA.KR', re: /\bкрим\b|крым|crimea/i },
  { hasc: 'UA.ZK', re: /закарпат|transcarpath|zakarpatt/i },
  { hasc: 'UA.VO', re: /волинськ|волын|volyn/i },
  { hasc: 'UA.LV', re: /львівськ|львовск|lvivska|lviv\s+oblast|l'vivs?ka/i },
  { hasc: 'UA.IF', re: /івано-франків|ивано-франк|ivano-frankivs/i },
  { hasc: 'UA.CV', re: /чернівец|черновц|chernivtsi|chernovts|чернівецьк|chernivets/i },
  { hasc: 'UA.CH', re: /чернігівськ|черниговск|chernihivska|chernigovska|чернігівщин|черниговщин|^чернігів$|^чернигов$/i },
  { hasc: 'UA.CK', re: /черкаськ|черкасс|cherkasy/i },
  { hasc: 'UA.ZT', re: /житомирськ|zhytomyr|zhytomyrska/i },
  { hasc: 'UA.VI', re: /вінницьк|vinnyts/i },
  { hasc: 'UA.DP', re: /дніпропетровськ|днепропетровск|dnipropetrovsk|dnipro\s+обл|дніпропетров/i },
  { hasc: 'UA.ZP', re: /запорізьк|запорожск|zaporizh/i },
  { hasc: 'UA.DT', re: /донецьк|донецк|donetsk/i },
  { hasc: 'UA.LH', re: /луганськ|луганск|luhansk|lugansk/i },
  { hasc: 'UA.KK', re: /харківськ|харьковск|kharkivska|kharkiv\s+oblast|харківщин/i },
  { hasc: 'UA.PL', re: /полтавськ|poltava/i },
  { hasc: 'UA.KH', re: /кіровоградськ|кропивниц|kirovohrad|kropyvnyts/i },
  { hasc: 'UA.RV', re: /рівненськ|ровенск|rivne/i },
  { hasc: 'UA.TP', re: /тернопільськ|ternopil|тернопол/i },
  { hasc: 'UA.KM', re: /хмельницьк|khmelnytsk/i },
  { hasc: 'UA.SM', re: /сумськ|sumy/i },
  { hasc: 'UA.KS', re: /херсонськ|kherson/i },
  { hasc: 'UA.MY', re: /миколаївськ|николаев|mykolaiv/i },
  { hasc: 'UA.OD', re: /одеськ|одесск|odeska|odessa|odesa/i },
];

function textToHasc(raw: string): string | null {
  const n = normalizeRegionText(raw);
  if (!n) return null;
  if (/^UA\.[A-Z]{2}$/i.test(n.trim())) {
    const code = n.trim().toUpperCase();
    if (getOblastIndex().hascSet.has(code)) return code;
  }
  for (const { hasc, re } of TEXT_TO_HASC) {
    if (re.test(n)) return hasc;
  }
  return null;
}

/**
 * Resolve stated administrative area from ingest fields (not `place` — too noisy for micro-locations).
 */
export function resolveStatedOblastHasc(marker: Record<string, unknown>): string | null {
  const direct = marker.resolved_oblast_hasc;
  if (typeof direct === 'string' && direct.trim()) {
    const h = direct.trim().toUpperCase();
    if (getOblastIndex().hascSet.has(h)) return h;
  }
  for (const key of ['region', 'oblast'] as const) {
    const v = marker[key];
    if (typeof v === 'string' && v.trim()) {
      const hasc = textToHasc(v);
      if (hasc) return hasc;
    }
  }
  return null;
}

/**
 * If coordinates fall in a different oblast than `region` / `oblast` / `resolved_oblast_hasc`
 * imply, snap to the stated oblast centroid and mark placement as approximate.
 * Manual markers are left unchanged.
 */
export function normalizeIngestMarkerRegionCoords(marker: Record<string, unknown>): void {
  if (marker.manual === true) return;

  // Predictive markers (e.g., approach paths) can validly cross oblast boundaries.
  // Do not snap them to the destination centroid.
  const rs = typeof marker.resolve_status === 'string' ? marker.resolve_status : '';
  const pm = typeof marker.placement_mode === 'string' ? marker.placement_mode : '';
  if (rs === 'trajectory_approach' || pm.startsWith('target_only') || pm === 'predictive') {
    return;
  }

  const stated = resolveStatedOblastHasc(marker);
  if (!stated) return;

  const idx = getOblastIndex();
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

  const atPoint = findHascContainingPoint(lat, lng);
  if (atPoint === stated) return;

  const centroid = idx.centroids[stated];
  if (!centroid) return;

  console.warn(
    `[REGION_CHECK] Stated ${stated} but coords in ${atPoint ?? 'unknown'} (${lat}, ${lng}) — snapping to oblast centroid`,
  );

  marker.lat = centroid.lat;
  marker.lng = centroid.lng;
  if (marker.placement_mode == null || marker.placement_mode === '') {
    marker.placement_mode = 'approximate';
  }
  if (marker.resolve_status == null || marker.resolve_status === '') {
    marker.resolve_status = 'region_mismatch';
  }
  if (typeof marker.confidence_0_100 === 'number' && Number.isFinite(marker.confidence_0_100)) {
    marker.confidence_0_100 = Math.min(marker.confidence_0_100, 45);
  } else if (typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)) {
    marker.confidence = Math.min(marker.confidence, 0.45);
  }
}

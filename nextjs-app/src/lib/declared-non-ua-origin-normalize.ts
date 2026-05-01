/**
 * Broad ingest guard: pipeline sometimes geocodes a Russian (or other non-target) place name
 * into a random point in Ukraine. If the message clearly names a known non-UA anchor but the
 * pin is hundreds of km away inside the threat bbox, snap to the declared anchor (approximate).
 *
 * Skips messages that likely describe an in-flight position or a UA target (trajectory / intercept).
 */

import { UKRAINE_THREAT_BOUNDS } from '@/lib/geo-bounds';
import { bumpForeignOriginFix } from '@/lib/pipeline-metrics';

function normalizeHaystack(s: string): string {
  return s
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/\s+/g, ' ')
    .trim();
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function inThreatBbox(lat: number, lng: number): boolean {
  return (
    lat >= UKRAINE_THREAT_BOUNDS.minLat &&
    lat <= UKRAINE_THREAT_BOUNDS.maxLat &&
    lng >= UKRAINE_THREAT_BOUNDS.minLng &&
    lng <= UKRAINE_THREAT_BOUNDS.maxLng
  );
}

/** UA target / trajectory wording — do not snap launch name to anchor (coords may be intercept). */
const SKIP_SNAP_RE =
  /(?:\bна\s+(?:харків|київ|києв|одес|одесс|дніпро|дніпр|запоріж|львів|суму|полтав|крив|миколаїв|чернігів|вінниц|хмельниц|тернопіл|рівн|ужгород|черкас|кропивниц|ужгород|івано-франків)|\bдо\s+(?:харків|київ|одес|дніпр|запоріж|львів)|-\s*(?:харків|київ|одес|дніпр)|[–—]\s*(?:харків|київ|одес|дніпр)|→\s*(?:харків|київ|одес)|курс\s+на|ціль\b|на\s+підльоті|trajectory|intercept|перехоп|в\s+напрямку\s+(?:харків|київ|одес|дніпр)|по\s+маршруту)/i;

type Anchor = { re: RegExp; lat: number; lng: number };

/**
 * Known non-UA places that appear in launch / origin lines. Regexes are conservative (city names,
 * not oblasts) to limit false matches inside longer Ukrainian toponyms.
 */
const NON_UA_ORIGIN_ANCHORS: Anchor[] = [
  { re: /таганрог|taganrog/i, lat: 47.2362, lng: 38.8678 },
  { re: /белгород|бєлгород|belgorod/i, lat: 50.5977, lng: 36.5878 },
  { re: /ростов[-\s]?на[-\s]?дону|rostov[-\s]?on[-\s]?don|\bростов\b/i, lat: 47.2357, lng: 39.7015 },
  { re: /\bкурск\b|kursk/i, lat: 51.7373, lng: 36.1874 },
  { re: /брянськ|брянск|bryansk/i, lat: 53.2434, lng: 34.3634 },
  { re: /воронеж|voronezh/i, lat: 51.672, lng: 39.1843 },
  { re: /міллерово|millerovo/i, lat: 48.9226, lng: 40.3975 },
  { re: /єйськ|yeysk|ейск/i, lat: 46.7056, lng: 38.2739 },
  { re: /морозовськ|morozovsk/i, lat: 48.351, lng: 41.876 },
  { re: /каменск[-\s]?шахтинск|kamensk-shakhtinsky/i, lat: 48.317, lng: 40.261 },
  { re: /енгельс\b|engels\b/i, lat: 51.485, lng: 46.126 },
  { re: /саратов\b|saratov\b/i, lat: 51.592, lng: 45.961 },
  { re: /орел\b|орёл\b|oryol\b/i, lat: 52.97, lng: 36.064 },
  { re: /ліпецьк|lipetsk/i, lat: 52.609, lng: 39.599 },
  { re: /тамбов\b|tambov\b/i, lat: 52.721, lng: 41.452 },
  { re: /валуйки|valuyki/i, lat: 50.211, lng: 38.099 },
  { re: /сольці|soltsy/i, lat: 58.12, lng: 30.309 },
  { re: /псков\b|pskov\b/i, lat: 57.819, lng: 28.332 },
  { re: /смоленськ|smolensk/i, lat: 54.782, lng: 32.045 },
  { re: /клинці|klintsy/i, lat: 52.752, lng: 32.234 },
  { re: /новозибков|novozybkov/i, lat: 52.539, lng: 31.934 },
  { re: /гомель\b|homiel|gomel\b/i, lat: 52.425, lng: 30.975 },
  { re: /мазир\b|mozyr\b/i, lat: 52.049, lng: 29.269 },
  { re: /брест\b|brest\b/i, lat: 52.097, lng: 23.734 },
  { re: /севастопол|sevastopol/i, lat: 44.616, lng: 33.525 },
  { re: /сімферопол|simferopol/i, lat: 44.952, lng: 34.102 },
  { re: /керч\b|kerch\b/i, lat: 45.357, lng: 36.468 },
  { re: /феодосі|feodosi/i, lat: 45.029, lng: 35.379 },
];

/**
 * Min distance between pin and declared anchor to treat geocode as wrong (km).
 * Below ~280 km (e.g. Taganrog → Kharkiv) we do not snap — may be intercept / forward position.
 */
const MIN_PIN_ANCHOR_DISCREPANCY_KM = 320;

export function normalizeDeclaredNonUaOriginCoords(marker: Record<string, unknown>): void {
  if (marker.manual === true) return;

  const clat = Number(marker.lat);
  const clng = Number(marker.lng);
  if (!Number.isFinite(clat) || !Number.isFinite(clng)) return;
  if (!inThreatBbox(clat, clng)) return;

  const parts: string[] = [];
  for (const key of ['origin', 'place', 'region', 'oblast'] as const) {
    const v = marker[key];
    if (typeof v === 'string' && v.trim()) parts.push(v);
  }
  const tx = marker.text;
  if (typeof tx === 'string' && tx.trim()) parts.push(tx.slice(0, 400));
  const hayRaw = parts.join(' ');
  const hay = normalizeHaystack(hayRaw);
  if (!hay || SKIP_SNAP_RE.test(hayRaw)) return;

  for (const { re, lat: aLat, lng: aLng } of NON_UA_ORIGIN_ANCHORS) {
    if (!re.test(hay)) continue;
    const d = haversineKm(clat, clng, aLat, aLng);
    if (d < MIN_PIN_ANCHOR_DISCREPANCY_KM) return;

    console.warn(
      `[DECLARED_NON_UA_ORIGIN] ${re.source}: pin ${clat.toFixed(3)},${clng.toFixed(3)} is ${Math.round(d)}km from ` +
        `declared anchor — snapping to ${aLat.toFixed(3)},${aLng.toFixed(3)}`,
    );
    bumpForeignOriginFix();
    marker.lat = aLat;
    marker.lng = aLng;
    if (marker.placement_mode == null || marker.placement_mode === '') {
      marker.placement_mode = 'approximate';
    }
    if (
      marker.resolve_status == null ||
      marker.resolve_status === '' ||
      marker.resolve_status === 'ok'
    ) {
      marker.resolve_status = 'foreign_origin_geocode_fix';
    }
    if (typeof marker.confidence_0_100 === 'number' && Number.isFinite(marker.confidence_0_100)) {
      marker.confidence_0_100 = Math.min(marker.confidence_0_100, 52);
    } else if (typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)) {
      marker.confidence = Math.min(marker.confidence, 0.52);
    }
    return;
  }
}

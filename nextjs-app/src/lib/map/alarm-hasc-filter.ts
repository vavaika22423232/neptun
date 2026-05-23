import type { Alarm } from '@/types';
import { REGION_TO_OBLAST_ID } from '@/lib/constants';

/** Нормалізація назви регіону для порівняння з GeoJSON (`rayon`, NL_NAME_1, …). */
export function normalizeAlarmRegionName(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/['ʼ’‘`´ʹʻ]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const DISTRICT_NAME_ALIASES: Record<string, string[]> = {
  // 2024 rename: Новомосковський район -> Самарівський район. Our raion GeoJSON still
  // carries the 2020 name, while UkraineAlarm already sends the new district name.
  [normalizeAlarmRegionName('Самарівський район')]: [
    'Самарівський район',
    'Самарський район',
    'Самарский район',
    'Новомосковський район',
    'Новомосковский район',
  ],
  [normalizeAlarmRegionName('Самарський район')]: [
    'Самарівський район',
    'Самарський район',
    'Самарский район',
    'Новомосковський район',
    'Новомосковский район',
  ],
  [normalizeAlarmRegionName('Самарский район')]: [
    'Самарівський район',
    'Самарський район',
    'Самарский район',
    'Новомосковський район',
    'Новомосковский район',
  ],
  [normalizeAlarmRegionName('Новомосковський район')]: [
    'Новомосковський район',
    'Самарівський район',
    'Самарський район',
    'Самарский район',
    'Новомосковский район',
  ],
  [normalizeAlarmRegionName('Новомосковский район')]: [
    'Новомосковський район',
    'Самарівський район',
    'Самарський район',
    'Самарский район',
    'Новомосковский район',
  ],
  // GeoJSON is based on older administrative names, while alarm providers may
  // use renamed districts.
  [normalizeAlarmRegionName('Звягельський район')]: [
    'Звягельський район',
    'Новоград-Волинський район',
  ],
  [normalizeAlarmRegionName('Новоград-Волинський район')]: [
    'Новоград-Волинський район',
    'Звягельський район',
  ],
  [normalizeAlarmRegionName('Володимирський район')]: [
    'Володимирський район',
    'Володимир-Волинський район',
  ],
  [normalizeAlarmRegionName('Володимир-Волинський район')]: [
    'Володимир-Волинський район',
    'Володимирський район',
  ],
  [normalizeAlarmRegionName('Шептицький район')]: [
    'Шептицький район',
    'Червоноградський район',
  ],
  [normalizeAlarmRegionName('Червоноградський район')]: [
    'Червоноградський район',
    'Шептицький район',
  ],
};

export function alarmRegionNameAliases(value: string): string[] {
  const original = String(value || '').trim();
  if (!original) return [];
  const aliases = DISTRICT_NAME_ALIASES[normalizeAlarmRegionName(original)] ?? [original];
  return [...new Set([original, ...aliases].filter(Boolean))];
}

function isDistrictRegion(alarm: Alarm): boolean {
  return String(alarm.regionType || '').toLowerCase() === 'district';
}

/** Активна тривога рівня області/республіки: не район (API інколи не шле `State`). */
export function isOblastLevelAlarm(alarm: Alarm): boolean {
  if (!alarm.activeAlerts?.length) return false;
  if (isDistrictRegion(alarm)) return false;
  return true;
}

/** Мінімальний контракт для `ukraine_oblasts.geojson` (GADM). */
export type OblastFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    properties?: Record<string, unknown> | null;
    geometry?: unknown;
  }>;
};

/** Maps GeoJSON oblast row → official UA-xx admin code (same list as worker `REGION_TO_OBLAST_ID`). */
function uaAdminCodeForOblastGeoProperties(props: Record<string, unknown>): string | null {
  const nl = normalizeAlarmRegionName(String(props.NL_NAME_1 || ''));
  const en = normalizeAlarmRegionName(String(props.NAME_1 || ''));
  if (!nl && !en) return null;
  let best: { code: string; labelLen: number } | null = null;
  for (const [label, code] of Object.entries(REGION_TO_OBLAST_ID)) {
    const L = normalizeAlarmRegionName(label);
    if (L.length < 4) continue;
    const hit =
      (nl && (nl.includes(L) || L.includes(nl))) || (en && (en.includes(L) || L.includes(en)));
    if (!hit) continue;
    if (!best || label.length > best.labelLen) best = { code, labelLen: label.length };
  }
  return best?.code ?? null;
}

/**
 * Підбирає HASC_1 (UA.XX) для активних обласних тривог, щоб фільтрувати GeoJSON шар.
 * Спочатку збіг regionId з HASC / ISO; інакше — м’яке співставлення з NL_NAME_1 / NAME_1.
 */
export function hascListForStateAlarms(alarms: Alarm[], oblastGeoJson: OblastFeatureCollection): string[] {
  const hascs = new Set<string>();
  const feats = oblastGeoJson.features || [];

  const norm = normalizeAlarmRegionName;

  for (const region of alarms) {
    if (!isOblastLevelAlarm(region)) continue;

    const rid = String(region.regionId || '').trim();
    const rname = norm(region.regionName || '');

    let found: string | null = null;

    for (const f of feats) {
      const p = f.properties as Record<string, unknown> | null | undefined;
      if (!p) continue;
      const hasc = String(p.HASC_1 || '');
      if (!hasc || hasc === '?') continue;

      const ridUpper = rid.toUpperCase();
      const letterTail = hasc.split('.')[1]?.toUpperCase();
      const adminFromPolygon = uaAdminCodeForOblastGeoProperties(p);
      if (
        rid &&
        (hasc === rid ||
          hasc.replace('.', '-') === rid ||
          (letterTail && `UA-${letterTail}` === ridUpper) ||
          String(p.GID_1 || '') === rid ||
          (adminFromPolygon && adminFromPolygon.toUpperCase() === ridUpper))
      ) {
        found = hasc;
        break;
      }
      const nl = norm(String(p.NL_NAME_1 || ''));
      const en = norm(String(p.NAME_1 || ''));
      if (rname && (nl && (rname.includes(nl) || nl.includes(rname)) || (en && (rname.includes(en) || en.includes(rname))))) {
        found = hasc;
        break;
      }
    }

    if (found) hascs.add(found);
  }

  return [...hascs];
}

/** Нормалізовані назви районів з активних тривог — для GeoJSON `rayon`. */
export function districtRegionNamesForAlarms(alarms: Alarm[]): string[] {
  const names = new Set<string>();
  for (const alarm of alarms) {
    if (!isDistrictRegion(alarm) || !alarm.activeAlerts?.length) continue;
    for (const alias of alarmRegionNameAliases(alarm.regionName || '')) {
      const name = normalizeAlarmRegionName(alias);
      if (name) names.add(name);
    }
  }
  return [...names];
}

/** `regionId` з активних районних тривог — використовується SVG/renderer-шарами районів. */
export function districtRegionIdsForAlarms(alarms: Alarm[]): string[] {
  const ids = new Set<string>();
  for (const region of alarms) {
    if (!isDistrictRegion(region) || !region.activeAlerts?.length) continue;
    const id = String(region.regionId || '').trim();
    if (id) ids.add(id);
  }
  return [...ids];
}

/** Oblast HASC_1 для вільного тексту області (resolver / інжест). */
export function findOblastHascForRegionLabel(
  regionLabel: string,
  oblastGeoJson: OblastFeatureCollection,
): string | null {
  const norm = normalizeAlarmRegionName(regionLabel);
  if (!norm) return null;

  let stem: string | null = null;
  if (norm.endsWith('щина') && norm.length >= 9) {
    stem = norm.slice(0, -4).trim();
    if (stem.length < 3) stem = null;
  }

  for (const f of oblastGeoJson.features || []) {
    const p = f.properties as Record<string, unknown> | null | undefined;
    if (!p) continue;
    const hasc = String(p.HASC_1 || '');
    if (!hasc || hasc === '?') continue;
    const nl = normalizeAlarmRegionName(String(p.NL_NAME_1 || ''));
    const en = normalizeAlarmRegionName(String(p.NAME_1 || ''));
    const hit =
      Boolean(nl && (norm.includes(nl) || nl.includes(norm))) ||
      Boolean(en && (norm.includes(en) || en.includes(norm))) ||
      Boolean(stem && ((nl && nl.includes(stem)) || (en && en.includes(stem))));
    if (hit) return hasc;
  }
  return null;
}

import type { Alarm } from '@/types';

/** Нормалізація назви регіону для порівняння з GeoJSON (`rayon`, NL_NAME_1, …). */
export function normalizeAlarmRegionName(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/['ʼ`]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
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

      if (
        rid &&
        (hasc === rid ||
          hasc.replace('.', '-') === rid ||
          `UA-${hasc.split('.')[1]}` === rid ||
          String(p.GID_1 || '') === rid)
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
    const name = normalizeAlarmRegionName(alarm.regionName || '');
    if (name) names.add(name);
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

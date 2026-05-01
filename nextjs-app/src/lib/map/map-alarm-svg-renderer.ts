import type { Alarm } from '@/types';

export type AlarmRegionType = Alarm['regionType'];
export type AlarmSvgKey = `${AlarmRegionType}:${string}`;

export type AlarmSvgRoots = {
  statesSvg: SVGElement | null;
  districtsSvg: SVGElement | null;
};

export type AlarmSvgRenderResult = {
  activeIds: Set<AlarmSvgKey>;
  added: number;
  removed: number;
  missing: AlarmSvgKey[];
};

export function collectActiveAlarmSvgKeys(alarms: Alarm[]): Set<AlarmSvgKey> {
  const active = new Set<AlarmSvgKey>();
  for (const region of alarms) {
    if (!region.activeAlerts?.length) continue;
    if (region.regionType !== 'State' && region.regionType !== 'District') continue;
    const id = String(region.regionId || '').trim();
    if (!id) continue;
    active.add(`${region.regionType}:${id}` as AlarmSvgKey);
  }
  return active;
}

function svgForAlarmKey(roots: AlarmSvgRoots, key: AlarmSvgKey): SVGElement | null {
  const [type] = key.split(':', 1);
  return type === 'State' ? roots.statesSvg : roots.districtsSvg;
}

function idForAlarmKey(key: AlarmSvgKey): string {
  return key.slice(key.indexOf(':') + 1);
}

function updateSvgAlarmClass(roots: AlarmSvgRoots, key: AlarmSvgKey, enabled: boolean): boolean {
  const svg = svgForAlarmKey(roots, key);
  if (!svg) return false;
  const id = idForAlarmKey(key);
  const escapedId =
    typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
      ? CSS.escape(id)
      : id.replace(/["\\]/g, '\\$&');
  const nodes = svg.querySelectorAll(`[id="${escapedId}"]`);
  if (nodes.length === 0) return false;
  nodes.forEach((el) => el.classList.toggle('alarm', enabled));
  return true;
}

export function renderAlarmSvgDiff(
  roots: AlarmSvgRoots,
  alarms: Alarm[],
  previousActiveIds: Set<AlarmSvgKey>,
): AlarmSvgRenderResult {
  const activeIds = collectActiveAlarmSvgKeys(alarms);
  const missing: AlarmSvgKey[] = [];
  let added = 0;
  let removed = 0;

  for (const key of previousActiveIds) {
    if (activeIds.has(key)) continue;
    if (updateSvgAlarmClass(roots, key, false)) {
      removed += 1;
    }
  }

  for (const key of activeIds) {
    if (previousActiveIds.has(key)) continue;
    if (updateSvgAlarmClass(roots, key, true)) {
      added += 1;
    } else {
      missing.push(key);
    }
  }

  return { activeIds, added, removed, missing };
}

import AsyncStorage from '@react-native-async-storage/async-storage';
import type { AlarmRow } from '../types/map';

const PREV_ACTIVE_KEY = 'expo_alarm_stats_prev_active_v1';

/** Flutter-compatible analytics keys (`alarm_tracking_service.dart`). */
function statsTotalAlarmsKey() {
  return 'stats_total_alarms';
}
function statsTotalMinutesKey() {
  return 'stats_total_minutes';
}

export function parseAlarmsPayload(data: unknown): AlarmRow[] {
  if (Array.isArray(data)) return data as AlarmRow[];
  if (data && typeof data === 'object' && Array.isArray((data as { alarms?: unknown }).alarms)) {
    return (data as { alarms: AlarmRow[] }).alarms;
  }
  return [];
}

function safeRegionKey(name: string): string {
  return name.replace(/[^\w\u0400-\u04FFіїєґІЇЄҐ]/gi, '_');
}

function activeRegionsFromAlarms(alarms: AlarmRow[]): Set<string> {
  const set = new Set<string>();
  for (const row of alarms) {
    const alerts = row.activeAlerts || [];
    if (alerts.length === 0) continue;
    const label = (row.regionName || row.regionId || '').trim();
    if (label) set.add(label);
  }
  return set;
}

let syncing = false;

/**
 * When a region gains any active alert → increment totals + heatmap (Flutter parity).
 * When all alerts clear → accumulate minutes since last start marker.
 */
export async function syncAlarmStatsFromRows(alarms: AlarmRow[]): Promise<void> {
  if (syncing) return;
  syncing = true;
  try {
    const nowActive = activeRegionsFromAlarms(alarms);
    const rawPrev = await AsyncStorage.getItem(PREV_ACTIVE_KEY);
    let prev = new Set<string>();
    try {
      const parsed = rawPrev ? (JSON.parse(rawPrev) as unknown) : [];
      if (Array.isArray(parsed)) prev = new Set(parsed.filter((x) => typeof x === 'string'));
    } catch {
      prev = new Set();
    }

    for (const region of nowActive) {
      if (!prev.has(region)) {
        const totalAlarms = Number((await AsyncStorage.getItem(statsTotalAlarmsKey())) || '0') || 0;
        await AsyncStorage.setItem(statsTotalAlarmsKey(), String(totalAlarms + 1));

        const sk = safeRegionKey(region);
        const hk = `heatmap_count_${sk}`;
        const heat = Number((await AsyncStorage.getItem(hk)) || '0') || 0;
        await AsyncStorage.setItem(hk, String(heat + 1));

        await AsyncStorage.setItem(`alarm_start_${sk}`, new Date().toISOString());
      }
    }

    for (const region of prev) {
      if (!nowActive.has(region)) {
        const sk = safeRegionKey(region);
        const startStr = await AsyncStorage.getItem(`alarm_start_${sk}`);
        if (startStr) {
          const start = Date.parse(startStr);
          if (Number.isFinite(start)) {
            const minutes = Math.max(0, Math.floor((Date.now() - start) / 60_000));
            if (minutes > 0) {
              const totalMin =
                Number((await AsyncStorage.getItem(statsTotalMinutesKey())) || '0') || 0;
              await AsyncStorage.setItem(statsTotalMinutesKey(), String(totalMin + minutes));
            }
          }
          await AsyncStorage.removeItem(`alarm_start_${sk}`);
        }
      }
    }

    await AsyncStorage.setItem(PREV_ACTIVE_KEY, JSON.stringify([...nowActive]));
  } finally {
    syncing = false;
  }
}

export async function getStatsTotals(): Promise<{ alarms: number; minutes: number }> {
  const a = Number((await AsyncStorage.getItem(statsTotalAlarmsKey())) || '0') || 0;
  const m = Number((await AsyncStorage.getItem(statsTotalMinutesKey())) || '0') || 0;
  return { alarms: a, minutes: m };
}

export type HeatmapEntry = { region: string; count: number };

export async function loadHeatmapEntries(): Promise<{
  rows: HeatmapEntry[];
  hasRegions: boolean;
}> {
  const keys = await AsyncStorage.getAllKeys();
  const counts = new Map<string, number>();
  for (const key of keys) {
    if (!key.startsWith('heatmap_count_')) continue;
    const n = Number((await AsyncStorage.getItem(key)) || '0') || 0;
    if (n <= 0) continue;
    const region = key.slice('heatmap_count_'.length).replace(/_/g, ' ');
    counts.set(region, n);
  }

  const selected = await AsyncStorage.getItem('selected_regions');
  let selectedNames: string[] = [];
  try {
    const parsed = selected ? (JSON.parse(selected) as unknown) : [];
    selectedNames = Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : [];
  } catch {
    selectedNames = [];
  }

  const merged = new Map<string, number>();
  for (const n of selectedNames) merged.set(n, counts.get(n) ?? 0);
  for (const [r, c] of counts) {
    if (!merged.has(r)) merged.set(r, c);
  }

  const rows = [...merged.entries()]
    .map(([region, count]) => ({ region, count }))
    .sort((x, y) => y.count - x.count);

  return { rows, hasRegions: selectedNames.length > 0 };
}

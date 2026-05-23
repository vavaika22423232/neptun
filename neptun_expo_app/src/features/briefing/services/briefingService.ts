import { endpoints } from '../../../config/api';
import { PrefsKeys } from '../../../config/prefsKeys';
import type { AlarmRow } from '../../../types/map';
import { apiRequest } from '../../../services/apiClient';
import { persistentStorage } from '../../../services/persistentStorage';
import type { BriefingData } from '../domain/briefingData';

const CACHE_KEY = 'briefing_offline_cache';
const CACHE_TS_KEY = 'briefing_offline_cache_ts';
const MEMORY_TTL_MS = 15 * 60 * 1000;
const OFFLINE_MAX_MS = 24 * 60 * 60 * 1000;

let memoryCache: BriefingData | null = null;
let memoryCacheAt = 0;

function normalizeRegionName(name: string): string {
  return name.trim().replace(/\s+область$/i, '').trim();
}

function userRegionNames(): Set<string> {
  const names = new Set<string>();
  for (const raw of persistentStorage.getStringList(PrefsKeys.selectedRegions)) {
    const t = raw.trim();
    if (!t) continue;
    names.add(t);
    names.add(normalizeRegionName(t));
  }
  return names;
}

function matchesUserRegion(apiName: string, userNames: Set<string>): boolean {
  const n = apiName.trim();
  if (userNames.has(n)) return true;
  return userNames.has(normalizeRegionName(n));
}

function parseAlarmsForBriefing(data: unknown): { total: number; regions: string[] } {
  const regions: string[] = [];
  const list = Array.isArray(data) ? data : (data as { list?: unknown })?.list;
  const rows = Array.isArray(list) ? list : [];
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue;
    const r = row as AlarmRow;
    const alerts = Array.isArray(r.activeAlerts) ? r.activeAlerts : [];
    if (alerts.length === 0) continue;
    const name = String(r.regionName ?? '').trim();
    if (name) regions.push(name);
  }
  return { total: regions.length, regions };
}

function parseThreatSummary(data: unknown): Pick<BriefingData, 'drones' | 'missiles' | 'kab' | 'ballistic'> {
  const summary = (data as { summary?: Record<string, unknown> })?.summary;
  if (!summary || typeof summary !== 'object') {
    return { drones: 0, missiles: 0, kab: 0, ballistic: 0 };
  }
  return {
    drones: Number(summary.drones ?? 0) || 0,
    missiles: Number(summary.missiles ?? 0) || 0,
    kab: Number(summary.kab ?? 0) || 0,
    ballistic: Number(summary.ballistic ?? 0) || 0,
  };
}

function loadOfflineCache(): BriefingData | null {
  const ts = Number(persistentStorage.getString(CACHE_TS_KEY) ?? '0');
  if (!ts || Date.now() - ts > OFFLINE_MAX_MS) return null;
  const raw = persistentStorage.getString(CACHE_KEY);
  if (!raw) return null;
  try {
    const json = JSON.parse(raw) as BriefingData;
    return { ...json, fromCache: true };
  } catch {
    return null;
  }
}

function saveOfflineCache(data: BriefingData): void {
  const { fromCache: _fc, ...payload } = data;
  persistentStorage.setString(CACHE_KEY, JSON.stringify(payload));
  persistentStorage.setString(CACHE_TS_KEY, String(Date.now()));
}

function buildBriefing(
  alarms: { total: number; regions: string[] },
  threats: Pick<BriefingData, 'drones' | 'missiles' | 'kab' | 'ballistic'>,
  fromCache: boolean,
): BriefingData {
  const hour = new Date().getHours();
  const userNames = userRegionNames();
  const selected = persistentStorage.getStringList(PrefsKeys.selectedRegions);
  const userRegionAlarmCount = alarms.regions.filter((r) => matchesUserRegion(r, userNames)).length;
  const displayRegion = selected[0]?.trim() || null;

  return {
    isMorning: hour < 12,
    totalAlarmsToday: alarms.total,
    alarmRegions: alarms.regions,
    ...threats,
    userRegionName: displayRegion,
    userRegionAlarmCount,
    userRegionsTotal: selected.length,
    fromCache,
  };
}

function emptyBriefing(): BriefingData {
  return buildBriefing({ total: 0, regions: [] }, { drones: 0, missiles: 0, kab: 0, ballistic: 0 }, false);
}

export const briefingService = {
  invalidateCache(): void {
    memoryCache = null;
    memoryCacheAt = 0;
  },

  async fetchBriefing(): Promise<BriefingData> {
    if (memoryCache && Date.now() - memoryCacheAt < MEMORY_TTL_MS) {
      return memoryCache;
    }

    let alarmsOk = false;
    let threatsOk = false;
    let alarms = { total: 0, regions: [] as string[] };
    let threats = { drones: 0, missiles: 0, kab: 0, ballistic: 0 };

    const [alarmsResult, threatsResult] = await Promise.allSettled([
      apiRequest<unknown>(endpoints.alarmsAll),
      apiRequest<unknown>(`${endpoints.threats}?timeRange=1440`),
    ]);

    if (alarmsResult.status === 'fulfilled') {
      alarms = parseAlarmsForBriefing(alarmsResult.value);
      alarmsOk = true;
    }
    if (threatsResult.status === 'fulfilled') {
      threats = parseThreatSummary(threatsResult.value);
      threatsOk = true;
    }

    if (!alarmsOk && !threatsOk) {
      const offline = loadOfflineCache();
      if (offline) {
        memoryCache = offline;
        memoryCacheAt = Date.now();
        return offline;
      }
      return emptyBriefing();
    }

    const data = buildBriefing(alarms, threats, false);
    memoryCache = data;
    memoryCacheAt = Date.now();
    saveOfflineCache(data);
    return data;
  },
};

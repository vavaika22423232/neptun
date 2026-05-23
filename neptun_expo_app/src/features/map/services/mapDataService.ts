import { endpoints } from '../../../config/api';
import type { AlarmRow, MapAlarmData, MapMarkerData, ThreatType } from '../../../types/map';
import { alarmsDataService } from '../../../services/alarmsDataService';
import { apiGetWithEtag } from '../../../services/apiClient';
import { storage } from '../../../services/storage';
import { parseThreatMarker } from '../utils/parseThreatMarker';

const regionNames: Record<string, string> = {
  '1': 'Вінницька область',
  '2': 'Волинська область',
  '3': 'Дніпропетровська область',
  '4': 'Донецька область',
  '5': 'Житомирська область',
  '6': 'Закарпатська область',
  '7': 'Запорізька область',
  '8': 'Івано-Франківська область',
  '9': 'Київська область',
  '10': 'Кіровоградська область',
  '11': 'Луганська область',
  '12': 'Львівська область',
  '13': 'Миколаївська область',
  '14': 'Одеська область',
  '15': 'Полтавська область',
  '16': 'Рівненська область',
  '17': 'Сумська область',
  '18': 'Тернопільська область',
  '19': 'Харківська область',
  '20': 'Херсонська область',
  '21': 'Хмельницька область',
  '22': 'Черкаська область',
  '23': 'Чернівецька область',
  '24': 'Чернігівська область',
  '25': 'м. Київ',
  '26': 'АР Крим',
  '27': 'м. Севастополь',
};

let markersEtag: string | null = null;
let cachedAlarms: MapAlarmData | null = null;
let cachedMarkers: MapMarkerData | null = null;

function classifyThreat(alertType: string): ThreatType | undefined {
  if (alertType === 'DRONES' || alertType.includes('DRONE')) return 'shahed';
  if (alertType === 'BALLISTIC' || alertType === 'MISSILE' || alertType.includes('BALLISTIC')) return 'raketa';
  if (alertType === 'AIR') return 'avia';
  return undefined;
}

export function parseAlarmData(data: unknown): MapAlarmData {
  const stateAlarms: Record<string, boolean> = {};
  const districtAlarms: Record<string, boolean> = {};
  const stateThreatTypes: Record<string, ThreatType> = {};
  const ballisticRegions = new Set<string>();
  let stateCount = 0;
  let districtCount = 0;

  if (Array.isArray(data)) {
    for (const row of data as AlarmRow[]) {
      const regionId = row.regionId?.toString();
      if (!regionId) continue;
      const alerts = Array.isArray(row.activeAlerts) ? row.activeAlerts : [];
      const hasAlarm = alerts.length > 0;
      const name = row.regionName || regionNames[regionId] || regionId;
      if (row.regionType === 'State') {
        stateAlarms[regionId] = hasAlarm;
        if (hasAlarm) stateCount += 1;
      } else if (row.regionType === 'District') {
        districtAlarms[regionId] = hasAlarm;
        if (hasAlarm) districtCount += 1;
      }
      for (const alert of alerts) {
        const type = String(alert.type ?? '');
        const classified = classifyThreat(type);
        if (classified && row.regionType === 'State') stateThreatTypes[regionId] = classified;
        if (classified === 'raketa') ballisticRegions.add(name);
      }
    }
  } else if (data && typeof data === 'object') {
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const hasAlarm =
        typeof value === 'boolean'
          ? value
          : !!(value && typeof value === 'object' && (value as { alarm?: boolean }).alarm);
      stateAlarms[key] = hasAlarm;
      if (hasAlarm) stateCount += 1;
    }
  }

  return {
    stateAlarms,
    districtAlarms,
    stateThreatTypes,
    stateCount,
    districtCount,
    ballisticRegions: [...ballisticRegions],
  };
}

export const mapDataService = {
  async fetchAlarms(): Promise<MapAlarmData> {
    try {
      const raw = await alarmsDataService.fetchRaw();
      cachedAlarms = parseAlarmData(raw);
      await storage.setJson('map_cache_alarms_v1', cachedAlarms);
      return cachedAlarms;
    } catch {
      return cachedAlarms ?? (await storage.getJson<MapAlarmData>('map_cache_alarms_v1', {
        stateAlarms: {},
        districtAlarms: {},
        stateThreatTypes: {},
        stateCount: 0,
        districtCount: 0,
        ballisticRegions: [],
      }));
    }
  },

  async fetchThreatMarkers(timeRange: number): Promise<MapMarkerData> {
    try {
      const response = await apiGetWithEtag<unknown>(`${endpoints.data}?timeRange=${timeRange}`, markersEtag);
      if (response.status === 304 && cachedMarkers) return cachedMarkers;
      markersEtag = response.etag;
      const root = response.data;
      const records = Array.isArray(root)
        ? root
        : root && typeof root === 'object'
          ? ((root as { tracks?: unknown[]; items?: unknown[] }).tracks ??
            (root as { tracks?: unknown[]; items?: unknown[] }).items ??
            [])
          : [];
      const markers = records.map(parseThreatMarker).filter((m): m is NonNullable<typeof m> => !!m);
      const counts = markers.reduce<Record<string, number>>((acc, marker) => {
        acc[marker.threatType] = (acc[marker.threatType] ?? 0) + 1;
        return acc;
      }, {});
      const ballistic =
        root && typeof root === 'object' ? (root as { ballistic_threat?: { active?: boolean; region?: string } }).ballistic_threat : undefined;
      cachedMarkers = {
        markers,
        counts,
        ballisticActive: ballistic?.active,
        ballisticRegion: ballistic?.region,
      };
      await storage.setJson('map_cache_markers_v1', cachedMarkers);
      return cachedMarkers;
    } catch {
      return cachedMarkers ?? (await storage.getJson<MapMarkerData>('map_cache_markers_v1', {
        markers: [],
        counts: {},
        ballisticActive: null,
        ballisticRegion: null,
      }));
    }
  },
};

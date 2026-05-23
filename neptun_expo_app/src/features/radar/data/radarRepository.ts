import { endpoints } from '../../../config/api';
import { apiRequest } from '../../../services/apiClient';
import type { RadarSnapshot } from '../domain/radarSnapshot';
import { normalizeThreatMarker, parseThreatsEnvelope } from './radarParsing';
import { radarSnapshotCache } from './radarSnapshotCache';

export { countActiveRegionsFromAlarmStream, normalizeThreatMarker, parseThreatsEnvelope } from './radarParsing';

export const radarRepository = {
  async fetchSnapshot(historyMinutes: number): Promise<RadarSnapshot> {
    try {
      const snap = await fetchFromNetwork(historyMinutes);
      await radarSnapshotCache.save(snap);
      return snap;
    } catch {
      const cached = await radarSnapshotCache.load();
      if (cached) return cached;
      throw new Error('Radar snapshot unavailable');
    }
  },
};

async function fetchFromNetwork(historyMinutes: number): Promise<RadarSnapshot> {
  const [threatsBody, alarmBody] = await Promise.all([
    apiRequest<unknown>(`${endpoints.threats}?timeRange=${historyMinutes}`),
    apiRequest<unknown>(endpoints.alarmStatus).catch(() => null),
  ]);

  const markers = parseThreatsEnvelope(threatsBody).map(normalizeThreatMarker);

  let active = 0;
  if (alarmBody != null && typeof alarmBody === 'object') {
    const alerts = (alarmBody as Record<string, unknown>).alerts;
    active = alerts != null && typeof alerts === 'object' ? Object.keys(alerts).length : 0;
  }

  return {
    markers,
    activeOblastsUnderAlarm: active,
    fetchedAt: Date.now(),
  };
}

import { endpoints } from './api';
import { apiRequest } from '../services/apiClient';
import { persistentStorage } from '../services/persistentStorage';

const CACHE_KEY = 'neptun_remote_config_v1';

export type RemoteConfig = {
  mapEngine: 'embed' | 'native';
  mapStyleUrl?: string;
  radarHistoryMinutesFree: number;
  radarHistoryMinutesPro: number;
  featureFlags: Record<string, boolean>;
  fetchedAt: number;
};

const DEFAULT_CONFIG: RemoteConfig = {
  mapEngine: 'embed',
  radarHistoryMinutesFree: 30,
  radarHistoryMinutesPro: 180,
  featureFlags: {},
  fetchedAt: 0,
};

function parseConfig(body: Record<string, unknown>): RemoteConfig {
  const flags =
    body.feature_flags != null && typeof body.feature_flags === 'object'
      ? (body.feature_flags as Record<string, boolean>)
      : {};

  const mapEngineRaw = String(body.map_engine ?? body.mapEngine ?? 'embed').toLowerCase();

  return {
    mapEngine: mapEngineRaw === 'native' ? 'native' : 'embed',
    mapStyleUrl:
      typeof body.map_style_url === 'string'
        ? body.map_style_url
        : typeof body.mapStyleUrl === 'string'
          ? body.mapStyleUrl
          : undefined,
    radarHistoryMinutesFree: Number(body.radar_history_minutes_free ?? 30) || 30,
    radarHistoryMinutesPro: Number(body.radar_history_minutes_pro ?? 180) || 180,
    featureFlags: flags,
    fetchedAt: Date.now(),
  };
}

export const remoteConfigService = {
  getCached(): RemoteConfig {
    const raw = persistentStorage.getString(CACHE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    try {
      return { ...DEFAULT_CONFIG, ...(JSON.parse(raw) as RemoteConfig) };
    } catch {
      return DEFAULT_CONFIG;
    }
  },

  async fetch(signal?: AbortSignal): Promise<RemoteConfig> {
    try {
      const body = await apiRequest<Record<string, unknown>>(endpoints.appRequirements, {
        timeoutMs: 8000,
        signal,
      });
      const config = parseConfig(body);
      persistentStorage.setString(CACHE_KEY, JSON.stringify(config));
      return config;
    } catch {
      return this.getCached();
    }
  },

  isEnabled(config: RemoteConfig, flag: string, defaultValue = false): boolean {
    if (flag in config.featureFlags) return !!config.featureFlags[flag];
    return defaultValue;
  },
};

import { endpoints } from '../config/api';
import { apiGetWithEtag } from './apiClient';
import { appLogger } from '../core/logging/appLogger';
import { storage } from './storage';

let etag: string | null = null;
let cachedPayload: unknown | null = null;
let lastNetworkMs = 0;

/** Minimum gap before another network fetch (dedupes map + AppContext callers). */
const DEDUPE_MS = 12_000;

/**
 * Shared `/api/alarms/all` fetch with ETag + in-memory dedupe.
 * Map and analytics stats should use this instead of separate `apiRequest` calls.
 */
export const alarmsDataService = {
  async fetchRaw(forceNetwork = false): Promise<unknown> {
    const now = Date.now();
    if (!forceNetwork && cachedPayload != null && now - lastNetworkMs < DEDUPE_MS) {
      return cachedPayload;
    }

    try {
      const response = await apiGetWithEtag<unknown>(endpoints.alarmsAll, etag);
      if (response.status === 304 && cachedPayload != null) {
        lastNetworkMs = now;
        return cachedPayload;
      }
      etag = response.etag;
      cachedPayload = response.data ?? cachedPayload;
      lastNetworkMs = now;
      if (cachedPayload != null) {
        await storage.setJson('alarms_raw_cache_v1', cachedPayload);
      }
      return cachedPayload ?? [];
    } catch (e) {
      appLogger.error('api', 'alarms/all fetch failed', e);
      if (cachedPayload != null) return cachedPayload;
      const disk = await storage.getJson<unknown>('alarms_raw_cache_v1', []);
      cachedPayload = disk;
      return disk;
    }
  },

  invalidate(): void {
    etag = null;
  },
};

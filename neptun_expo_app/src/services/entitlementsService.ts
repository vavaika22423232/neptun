import { PrefsKeys } from '../config/prefsKeys';
import { endpoints } from '../config/api';
import type { EntitlementsPayload, PlanId } from '../features/monetization/types';
import { FREE_ENTITLEMENTS } from '../features/monetization/types';
import {
  isV1MonetizationBackendAvailable,
  noteV1MonetizationHttpError,
  shouldLogV1MonetizationUnavailable,
} from '../features/monetization/services/monetizationBackend';
import { apiGet, apiRequest } from './apiClient';
import { appLogger } from '../core/logging/appLogger';
import { authService } from './authService';
import { persistentStorage } from './persistentStorage';
import { adService } from './adService';
import { monetizationConfigService } from '../features/monetization/services/monetizationConfigService';
import { safeJson } from '../utils/json';

const CACHE_KEY = 'entitlements_cache_v2';

let cached: EntitlementsPayload = FREE_ENTITLEMENTS;
const listeners = new Set<() => void>();
let bootstrapInFlight: Promise<EntitlementsPayload> | null = null;
let syncInFlight: Promise<EntitlementsPayload> | null = null;

function notify(): void {
  listeners.forEach((fn) => fn());
}

function loadCache(): EntitlementsPayload {
  const raw = persistentStorage.getString(CACHE_KEY);
  if (!raw) return FREE_ENTITLEMENTS;
  return safeJson(raw, FREE_ENTITLEMENTS);
}

function saveCache(ent: EntitlementsPayload): void {
  persistentStorage.setString(CACHE_KEY, JSON.stringify(ent));
}

function logV1UnavailableOnce(): void {
  if (!shouldLogV1MonetizationUnavailable()) return;
  appLogger.error(
    'purchase',
    'Monetization API v1 is unavailable on this server (404); using local entitlements',
  );
}

function logBootstrapFailure(error: unknown): void {
  noteV1MonetizationHttpError(error);
  if (!isV1MonetizationBackendAvailable()) {
    logV1UnavailableOnce();
    return;
  }
  appLogger.error('purchase', 'bootstrap failed', error);
}

function logSyncFailure(error: unknown): void {
  noteV1MonetizationHttpError(error);
  if (!isV1MonetizationBackendAvailable()) {
    logV1UnavailableOnce();
    return;
  }
  appLogger.error('purchase', 'entitlements sync failed', error);
}

async function authToken(): Promise<string | null> {
  let token = await authService.getAccessToken();
  if (!token) {
    await authService.login();
    token = await authService.getAccessToken();
  }
  return token;
}

export const entitlementsService = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  getCached(): EntitlementsPayload {
    return cached;
  },

  getPlan(): PlanId {
    return cached.plan;
  },

  isPaid(): boolean {
    return cached.isPro;
  },

  hasAdsDisabled(): boolean {
    return cached.features.adsDisabled;
  },

  async bootstrap(): Promise<EntitlementsPayload> {
    if (bootstrapInFlight) return bootstrapInFlight;

    bootstrapInFlight = (async () => {
      cached = loadCache();

      if (!isV1MonetizationBackendAvailable()) return cached;

      await monetizationConfigService.load();
      if (!isV1MonetizationBackendAvailable()) return cached;

      const deviceId = await authService.getDeviceId();
      if (!deviceId) return cached;

      try {
        const data = await apiRequest<{ entitlements?: EntitlementsPayload }>(endpoints.v1UsersBootstrap, {
          method: 'POST',
          body: JSON.stringify({ deviceId, platform: 'expo' }),
          authToken: await authToken(),
          timeoutMs: 18_000,
        });
        if (data.entitlements) {
          cached = data.entitlements;
          saveCache(cached);
          persistentStorage.setBoolean(PrefsKeys.isPremium, cached.isPro);
          persistentStorage.setString(PrefsKeys.activeTier, cached.plan);
          adService.syncAdsFromEntitlements(cached.features.adsDisabled);
          notify();
        }
      } catch (e) {
        logBootstrapFailure(e);
      }
      return cached;
    })().finally(() => {
      bootstrapInFlight = null;
    });

    return bootstrapInFlight;
  },

  async syncFromServer(): Promise<EntitlementsPayload> {
    if (!isV1MonetizationBackendAvailable()) return cached;
    if (syncInFlight) return syncInFlight;

    syncInFlight = (async () => {
      const deviceId = await authService.getDeviceId();
      if (!deviceId) return cached;

      try {
        const ent = await apiGet<EntitlementsPayload>(
          `${endpoints.v1MeEntitlements}?deviceId=${encodeURIComponent(deviceId)}`,
          { authToken: await authToken(), timeoutMs: 15_000 },
        );
        cached = ent;
        saveCache(cached);
        persistentStorage.setBoolean(PrefsKeys.isPremium, cached.isPro);
        persistentStorage.setString(PrefsKeys.activeTier, cached.plan);
        adService.syncAdsFromEntitlements(cached.features.adsDisabled);
        notify();
        return cached;
      } catch (e) {
        logSyncFailure(e);
        cached = loadCache();
        notify();
        return cached;
      }
    })().finally(() => {
      syncInFlight = null;
    });

    return syncInFlight;
  },

  applyServerEntitlements(ent: EntitlementsPayload): void {
    cached = ent;
    adService.syncAdsFromEntitlements(ent.features.adsDisabled);
    saveCache(ent);
    persistentStorage.setBoolean(PrefsKeys.isPremium, ent.isPro);
    persistentStorage.setString(PrefsKeys.activeTier, ent.plan);
    notify();
  },
};

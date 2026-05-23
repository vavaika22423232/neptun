import { endpoints } from '../../../config/api';
import type { EntitlementFeatures, PlanId } from '../types';
import { hasMinPlan } from '../types';
import { apiGet } from '../../../services/apiClient';
import {
  isV1MonetizationBackendAvailable,
  noteV1MonetizationHttpError,
} from './monetizationBackend';
import { safeJson } from '../../../utils/json';
import { persistentStorage } from '../../../services/persistentStorage';

const CACHE_KEY = 'monetization_remote_config_v1';

export type RemoteMonetizationConfig = {
  enableProPaywall: boolean;
  enableProPlus: boolean;
  enableMaxPlan: boolean;
  enableSmartNotifications: boolean;
  enableMyRadar: boolean;
  enableHistoryAnalytics: boolean;
  enableExtendedThreatCard: boolean;
  enableTelegramAdminMode: boolean;
  enableDailyReports: boolean;
  enableWeeklyReports: boolean;
  enableRewardedAdFree: boolean;
  enablePremiumMap: boolean;
  enableCustomSounds: boolean;
  enableQuietMode: boolean;
  enableServerEntitlements: boolean;
  paywall: { title: string; subtitle: string; proPlusBadge: string; maxBadge: string };
  rewarded: { adFreeHours: number; historyUnlockHours: number };
};

const FALLBACK: RemoteMonetizationConfig = {
  enableProPaywall: true,
  enableProPlus: true,
  enableMaxPlan: true,
  enableSmartNotifications: true,
  enableMyRadar: true,
  enableHistoryAnalytics: true,
  enableExtendedThreatCard: true,
  enableTelegramAdminMode: true,
  enableDailyReports: true,
  enableWeeklyReports: true,
  enableRewardedAdFree: true,
  enablePremiumMap: true,
  enableCustomSounds: true,
  enableQuietMode: true,
  enableServerEntitlements: true,
  paywall: {
    title: 'Більше контролю під час тривог',
    subtitle:
      'PRO відкриває розумні сповіщення, історію, персональний радар, аналітику та вимикає рекламу. Базова карта й важливі сповіщення залишаються безкоштовними.',
    proPlusBadge: 'Популярний',
    maxBadge: 'Для адмінів, медіа та тих, хто слідкує постійно',
  },
  rewarded: { adFreeHours: 4, historyUnlockHours: 24 },
};

let cached = FALLBACK;

export const monetizationConfigService = {
  get(): RemoteMonetizationConfig {
    return cached;
  },

  isFeatureEnabled(key: keyof RemoteMonetizationConfig): boolean {
    const v = cached[key];
    return typeof v === 'boolean' ? v : true;
  },

  async load(): Promise<RemoteMonetizationConfig> {
    const raw = persistentStorage.getString(CACHE_KEY);
    if (raw) cached = safeJson(raw, FALLBACK);

    if (!isV1MonetizationBackendAvailable()) return cached;

    try {
      const remote = await apiGet<RemoteMonetizationConfig>(endpoints.v1ConfigMonetization, {
        timeoutMs: 12_000,
      });
      cached = { ...FALLBACK, ...remote };
      persistentStorage.setString(CACHE_KEY, JSON.stringify(cached));
    } catch (e) {
      noteV1MonetizationHttpError(e);
    }
    return cached;
  },
};

export function requireFeature(
  features: EntitlementFeatures,
  flag: keyof EntitlementFeatures,
  minPlan: PlanId,
  currentPlan: PlanId,
): { allowed: boolean; requiredPlan: PlanId } {
  if (!hasMinPlan(currentPlan, minPlan)) {
    return { allowed: false, requiredPlan: minPlan };
  }
  const value = features[flag];
  if (typeof value === 'boolean' && !value) {
    return { allowed: false, requiredPlan: minPlan };
  }
  if (!monetizationConfigService.isFeatureEnabled(mapFlagToConfig(flag))) {
    return { allowed: false, requiredPlan: minPlan };
  }
  return { allowed: true, requiredPlan: minPlan };
}

function mapFlagToConfig(flag: keyof EntitlementFeatures): keyof RemoteMonetizationConfig {
  const map: Partial<Record<keyof EntitlementFeatures, keyof RemoteMonetizationConfig>> = {
    smartNotifications: 'enableSmartNotifications',
    premiumMap: 'enablePremiumMap',
    customSounds: 'enableCustomSounds',
    quietMode: 'enableQuietMode',
    extendedThreatCard: 'enableExtendedThreatCard',
    dailyReports: 'enableDailyReports',
    weeklyReports: 'enableWeeklyReports',
    telegramAdminMode: 'enableTelegramAdminMode',
  };
  return map[flag] ?? 'enableServerEntitlements';
}

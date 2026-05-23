import * as Application from 'expo-application';
import { Platform } from 'react-native';
import { AppConstants } from '../config/constants';
import { endpoints } from '../config/api';
import { apiRequest } from './apiClient';

export type AppUpdateBlockPayload = {
  title: string;
  message: string;
  androidStoreUrl: string;
  iosStoreUrl: string;
};

function compareSemver(a: string, b: string): number {
  const pa = a.split(/[+-]/)[0].split('.').map((x) => Number(x) || 0);
  const pb = b.split(/[+-]/)[0].split('.').map((x) => Number(x) || 0);
  const n = Math.max(pa.length, pb.length);
  for (let i = 0; i < n; i += 1) {
    const da = pa[i] ?? 0;
    const db = pb[i] ?? 0;
    if (da !== db) return da < db ? -1 : 1;
  }
  return 0;
}

export const appVersionGateService = {
  async evaluate(signal?: AbortSignal): Promise<{ ok: true } | { ok: false; block: AppUpdateBlockPayload }> {
    if (Platform.OS === 'web') return { ok: true };
    try {
      const req = await apiRequest<{
        min_version?: string;
        min_build?: number | string;
        title?: string;
        message?: string;
        android_store_url?: string;
        ios_store_url?: string;
      }>(endpoints.appRequirements, { timeoutMs: 8000, signal });
      const clientVersion = Application.nativeApplicationVersion || AppConstants.appVersion;
      const clientBuild = Number(Application.nativeBuildVersion || AppConstants.appBuildNumber) || 0;
      const minBuild = Number(req.min_build ?? 0) || 0;
      const belowBuild = minBuild > 0 && clientBuild < minBuild;
      const belowVersion = req.min_version ? compareSemver(clientVersion, req.min_version) < 0 : false;
      if (!belowBuild && !belowVersion) return { ok: true };
      return {
        ok: false,
        block: {
          title: req.title || 'Потрібне оновлення',
          message: req.message || 'Встановіть останню версію додатку, щоб продовжити.',
          androidStoreUrl: req.android_store_url || AppConstants.playStoreListingUrl,
          iosStoreUrl: req.ios_store_url || AppConstants.appStoreListingUrl,
        },
      };
    } catch {
      return { ok: true };
    }
  },
};

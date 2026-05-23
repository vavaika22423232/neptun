import * as Updates from 'expo-updates';

export type OtaCheckResult = {
  checked: boolean;
  available: boolean;
  fetched: boolean;
  error?: string;
};

/**
 * EAS Update startup check — downloads OTA bundle when available (no forced reload).
 * Mirrors Phase 5 OTA architecture in MIGRATION_ROADMAP.md.
 */
export const otaUpdateService = {
  async checkAndFetchOnStartup(): Promise<OtaCheckResult> {
    if (__DEV__) {
      return { checked: false, available: false, fetched: false };
    }
    try {
      if (!Updates.isEnabled) {
        return { checked: true, available: false, fetched: false };
      }
      const check = await Updates.checkForUpdateAsync();
      if (!check.isAvailable) {
        return { checked: true, available: false, fetched: false };
      }
      await Updates.fetchUpdateAsync();
      return { checked: true, available: true, fetched: true };
    } catch (e) {
      return {
        checked: true,
        available: false,
        fetched: false,
        error: e instanceof Error ? e.message : String(e),
      };
    }
  },

  async reloadIfReady(): Promise<void> {
    if (__DEV__ || !Updates.isEnabled) return;
    await Updates.reloadAsync();
  },
};

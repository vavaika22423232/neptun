import AsyncStorage from '@react-native-async-storage/async-storage';
import { MMKV } from 'react-native-mmkv';
import { PrefsKeys } from '../config/prefsKeys';

let mmkv: MMKV | null = null;

function getMmkv(): MMKV | null {
  if (mmkv) return mmkv;
  try {
    mmkv = new MMKV({ id: 'neptun-app' });
    return mmkv;
  } catch {
    return null;
  }
}

const memory = new Map<string, string>();

/**
 * Fast synchronous KV — MMKV when native module is linked, else in-memory + AsyncStorage hydrate.
 */
export const persistentStorage = {
  getString(key: string): string | undefined {
    const store = getMmkv();
    if (store) return store.getString(key);
    return memory.get(key);
  },

  setString(key: string, value: string): void {
    const store = getMmkv();
    if (store) store.set(key, value);
    else memory.set(key, value);
    void AsyncStorage.setItem(key, value).catch(() => undefined);
  },

  getBoolean(key: string, defaultValue = false): boolean {
    const raw = this.getString(key);
    if (raw == null) return defaultValue;
    return raw === 'true' || raw === '1';
  },

  setBoolean(key: string, value: boolean): void {
    this.setString(key, value ? 'true' : 'false');
  },

  getStringList(key: string): string[] {
    const raw = this.getString(key);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as unknown;
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  },

  setStringList(key: string, values: string[]): void {
    this.setString(key, JSON.stringify(values));
  },

  delete(key: string): void {
    getMmkv()?.delete(key);
    memory.delete(key);
    void AsyncStorage.removeItem(key).catch(() => undefined);
  },

  /** Load AsyncStorage into MMKV/memory on cold start. */
  async hydrateFromAsyncStorage(): Promise<void> {
    const keys = [
      ...Object.values(PrefsKeys),
      'selected_oblast_ids',
      'selected_raion_ids',
      'subscribed_topics',
      'quiet_hours_enabled',
      'quiet_hours_start',
      'quiet_hours_end',
      'quiet_hours_allow_critical',
      'notify_threat_types',
      'onboarding_region',
      'dedup_last_notification_key',
      'dedup_last_notification_time',
      'dedup_last_tts_key',
      'dedup_last_tts_time',
      'pending_ballistic_alert',
      'pending_ballistic_region',
      'pending_ballistic_time',
      PrefsKeys.changelogLastShownVersion,
      PrefsKeys.reviewAppLaunchCount,
      PrefsKeys.reviewFirstLaunchDate,
      PrefsKeys.reviewHasShownPrompt,
      PrefsKeys.batteryOptPromptLastShown,
      PrefsKeys.adFreeUntil,
      'last_app_open_ad_shown',
    ];
    const pairs = await AsyncStorage.multiGet(keys);
    for (const [key, value] of pairs) {
      if (value != null) memory.set(key, value);
      if (value != null) getMmkv()?.set(key, value);
    }
  },
};

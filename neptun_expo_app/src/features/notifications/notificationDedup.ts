import { persistentStorage } from '../../services/persistentStorage';

/** Flutter `_DedupStore` + in-memory foreground cache (30s). */
const NOTIF_KEY = 'dedup_last_notification_key';
const NOTIF_TIME = 'dedup_last_notification_time';
const TTS_KEY = 'dedup_last_tts_key';
const TTS_TIME = 'dedup_last_tts_time';
const FOREGROUND_TTL_MS = 30_000;
const TTS_TTL_MS = 60_000;

const foregroundCache = new Map<string, number>();

export const notificationDedup = {
  shouldSkipNotification(key: string, ttlMs = FOREGROUND_TTL_MS): boolean {
    const lastKey = persistentStorage.getString(NOTIF_KEY) ?? '';
    const lastTime = Number(persistentStorage.getString(NOTIF_TIME) ?? '0');
    const now = Date.now();
    if (key === lastKey && now - lastTime < ttlMs) return true;
    persistentStorage.setString(NOTIF_KEY, key);
    persistentStorage.setString(NOTIF_TIME, String(now));
    return false;
  },

  isDuplicateInMemory(key: string, ttlMs = FOREGROUND_TTL_MS): boolean {
    const last = foregroundCache.get(key);
    if (last == null) return false;
    return Date.now() - last < ttlMs;
  },

  markShownInMemory(key: string): void {
    foregroundCache.set(key, Date.now());
    const now = Date.now();
    for (const [k, t] of foregroundCache) {
      if (now - t > FOREGROUND_TTL_MS) foregroundCache.delete(k);
    }
  },

  /** Flutter `_DedupStore.shouldSkipTts` — sync foreground/background TTS. */
  shouldSkipTts(key: string, ttlMs = TTS_TTL_MS): boolean {
    const lastKey = persistentStorage.getString(TTS_KEY) ?? '';
    const lastTime = Number(persistentStorage.getString(TTS_TIME) ?? '0');
    const now = Date.now();
    if (key === lastKey && now - lastTime < ttlMs) return true;
    persistentStorage.setString(TTS_KEY, key);
    persistentStorage.setString(TTS_TIME, String(now));
    return false;
  },
};

import { Platform } from 'react-native';
import { PrefsKeys } from '../config/prefsKeys';
import { getExpoSpeech, isExpoSpeechAvailable } from '../utils/lazyExpoNative';
import { persistentStorage } from './persistentStorage';

const SPOKEN_CACHE_TTL_MS = 45_000;
const spokenCache = new Map<string, number>();

function normalizeCacheKey(text: string): string {
  return text.toLowerCase().trim().replace(/[.,!?]/g, '');
}

function wasRecentlySpoken(key: string): boolean {
  const t = spokenCache.get(key);
  if (t == null) return false;
  return Date.now() - t < SPOKEN_CACHE_TTL_MS;
}

function markSpoken(key: string): void {
  spokenCache.set(key, Date.now());
  const now = Date.now();
  for (const [k, time] of spokenCache) {
    if (now - time > 10 * 60_000) spokenCache.delete(k);
  }
}

let initialized = false;
let speaking = false;

export const ttsService = {
  isNativeAvailable(): boolean {
    return isExpoSpeechAvailable();
  },

  get diagnostics() {
    return {
      initialized,
      enabled: persistentStorage.getBoolean(PrefsKeys.ttsEnabled, false),
      speaking,
      nativeModule: isExpoSpeechAvailable(),
    };
  },

  async initialize(): Promise<void> {
    if (initialized) return;
    initialized = true;
    if (Platform.OS === 'web') return;

    const Speech = getExpoSpeech();
    if (!Speech) return;

    try {
      const voices = await Speech.getAvailableVoicesAsync();
      const uk = voices.find((v) => v.language?.toLowerCase().startsWith('uk'));
      if (uk?.identifier) {
        persistentStorage.setString(PrefsKeys.ttsLanguage, uk.identifier);
      }
    } catch {
      /* voices optional */
    }
  },

  async setEnabled(enabled: boolean): Promise<void> {
    persistentStorage.setBoolean(PrefsKeys.ttsEnabled, enabled);
  },

  async setVolume(volume: number): Promise<void> {
    persistentStorage.setString(PrefsKeys.ttsVolume, String(Math.max(0, Math.min(1, volume))));
  },

  getVolume(): number {
    return Number(persistentStorage.getString(PrefsKeys.ttsVolume) ?? '1') || 1;
  },

  isEnabled(): boolean {
    return persistentStorage.getBoolean(PrefsKeys.ttsEnabled, false);
  },

  /** Flutter `speakDirect` — bypasses enabled flag (caller checks settings). */
  async speakDirect(text: string): Promise<void> {
    if (Platform.OS === 'web' || !text.trim()) return;

    const Speech = getExpoSpeech();
    if (!Speech) return;

    await this.initialize();

    const cacheKey = normalizeCacheKey(text);
    if (wasRecentlySpoken(cacheKey)) return;
    markSpoken(cacheKey);

    const volume = this.getVolume();
    const voice = persistentStorage.getString(PrefsKeys.ttsLanguage);

    speaking = true;
    await new Promise<void>((resolve) => {
      Speech.speak(text, {
        language: 'uk-UA',
        volume,
        rate: 0.9,
        pitch: 1,
        ...(voice ? { voice } : {}),
        onDone: () => {
          speaking = false;
          resolve();
        },
        onStopped: () => {
          speaking = false;
          resolve();
        },
        onError: () => {
          speaking = false;
          resolve();
        },
      });
    });
  },

  async speakTest(): Promise<void> {
    if (!isExpoSpeechAvailable()) {
      throw new Error(
        'Голосовий модуль недоступний. Перезберіть dev client: npx expo run:ios --device',
      );
    }
    try {
      await this.speakDirect('Голосові сповіщення працюють!');
    } catch {
      throw new Error(
        'Голосовий модуль недоступний. Перезберіть dev client: npx expo run:ios --device',
      );
    }
  },

  async stop(): Promise<void> {
    const Speech = getExpoSpeech();
    if (!Speech) return;
    try {
      Speech.stop();
    } catch {
      /* ignore */
    }
    speaking = false;
  },
};

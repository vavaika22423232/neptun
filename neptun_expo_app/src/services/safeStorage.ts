import { safeJson } from '../utils/json';
import { persistentStorage } from './persistentStorage';
import { storage } from './storage';

/** Read string with default when missing. */
export function safeGetString(key: string, fallback = ''): string {
  return persistentStorage.getString(key) ?? fallback;
}

export function safeGetBoolean(key: string, fallback = false): boolean {
  return persistentStorage.getBoolean(key, fallback);
}

export function safeGetStringList(key: string): string[] {
  return persistentStorage.getStringList(key);
}

export function safeSetString(key: string, value: string): void {
  try {
    persistentStorage.setString(key, value);
  } catch {
    /* MMKV unavailable */
  }
}

export function safeSetBoolean(key: string, value: boolean): void {
  safeSetString(key, value ? 'true' : 'false');
}

export async function safeGetJson<T>(key: string, fallback: T): Promise<T> {
  try {
    return await storage.getJson<T>(key, fallback);
  } catch {
    return fallback;
  }
}

export async function safeSetJson<T>(key: string, value: T): Promise<void> {
  try {
    await storage.setJson(key, value);
  } catch {
    /* ignore */
  }
}

export function safeParseJson<T>(raw: string | undefined | null, fallback: T): T {
  if (!raw) return fallback;
  return safeJson<T>(raw, fallback);
}

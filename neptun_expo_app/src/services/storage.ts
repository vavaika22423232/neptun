import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { PrefsKeys } from '../config/prefsKeys';
import { persistentStorage } from './persistentStorage';

const fallback = new Map<string, string>();

async function read(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    return fallback.get(key) ?? null;
  }
}

async function write(key: string, value: string): Promise<void> {
  fallback.set(key, value);
  try {
    await AsyncStorage.setItem(key, value);
  } catch {
    /* memory fallback */
  }
}

async function readBool(key: string, defaultValue = false): Promise<boolean> {
  const value = await read(key);
  if (value == null) return defaultValue;
  return value === 'true' || value === '1';
}

async function writeBool(key: string, value: boolean): Promise<void> {
  await write(key, value ? 'true' : 'false');
}

async function secureGet(key: string): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(key);
  } catch {
    return read(`secure:${key}`);
  }
}

async function secureSet(key: string, value: string | null): Promise<void> {
  if (value == null) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      await AsyncStorage.removeItem(`secure:${key}`).catch(() => undefined);
    }
    return;
  }
  try {
    await SecureStore.setItemAsync(key, value);
  } catch {
    await write(`secure:${key}`, value);
  }
}

export const storage = {
  async getIsFirstLaunch() {
    return persistentStorage.getBoolean(PrefsKeys.firstLaunch, true);
  },
  async setFirstLaunch(value: boolean) {
    persistentStorage.setBoolean(PrefsKeys.firstLaunch, value);
    await writeBool(PrefsKeys.firstLaunch, value);
  },
  async isPremium() {
    return persistentStorage.getBoolean(PrefsKeys.isPremium, false);
  },
  async setPremium(value: boolean) {
    persistentStorage.setBoolean(PrefsKeys.isPremium, value);
    await writeBool(PrefsKeys.isPremium, value);
  },
  async getDeviceId() {
    let id = await secureGet('chat_device_id');
    if (!id) {
      id = `device_${Date.now()}_${Math.floor(Math.random() * 999999)}`;
      await secureSet('chat_device_id', id);
    }
    return id;
  },
  async getNickname() {
    return read('chat_nickname');
  },
  async setNickname(nickname: string | null) {
    if (nickname == null) await AsyncStorage.removeItem('chat_nickname').catch(() => undefined);
    else await write('chat_nickname', nickname);
  },
  async getModeratorSecret() {
    return secureGet('_mod_secret');
  },
  async setModeratorSecret(secret: string | null) {
    await secureSet('_mod_secret', secret);
    await writeBool('chat_moderator', !!secret);
  },
  async getProChatThemeId() {
    return read('pro_chat_theme_id');
  },
  async setProChatThemeId(id: string) {
    await write('pro_chat_theme_id', id);
  },
  async getProAnimatedAvatar() {
    return readBool('pro_animated_avatar', false);
  },
  async setProAnimatedAvatar(value: boolean) {
    await writeBool('pro_animated_avatar', value);
  },
  async getJson<T>(key: string, fallbackValue: T): Promise<T> {
    const value = await read(key);
    if (!value) return fallbackValue;
    try {
      return JSON.parse(value) as T;
    } catch {
      return fallbackValue;
    }
  },
  async setJson<T>(key: string, value: T): Promise<void> {
    await write(key, JSON.stringify(value));
  },
  async remove(key: string): Promise<void> {
    fallback.delete(key);
    await AsyncStorage.removeItem(key).catch(() => undefined);
  },

  secureGet: secureGet,
  secureSet: secureSet,
  async secureDelete(key: string): Promise<void> {
    await secureSet(key, null);
  },
};

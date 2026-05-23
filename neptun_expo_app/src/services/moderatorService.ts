import { API_BASE_URL, endpoints } from '../config/api';
import { PrefsKeys } from '../config/prefsKeys';
import { apiRequest } from './apiClient';
import { persistentStorage } from './persistentStorage';
import { storage } from './storage';

export const MODERATOR_SECRET_MAX = 256;

type Listener = (isModerator: boolean) => void;
const listeners = new Set<Listener>();

function notify(isModerator: boolean) {
  persistentStorage.setBoolean(PrefsKeys.isChatModerator, isModerator);
  for (const cb of listeners) cb(isModerator);
}

/** Mirrors Flutter `ModeratorService`. */
export const moderatorService = {
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  validateModeratorSecretInput(raw: string): string | null {
    const s = raw.trim();
    if (s.length < 6) return 'Введіть пароль';
    if (s.length > MODERATOR_SECRET_MAX) return 'Пароль занадто довгий';
    return null;
  },

  /** Cold start: sync moderator flag from secure storage (Flutter `ModeratorService.init`). */
  async init(): Promise<void> {
    const secret = await storage.getModeratorSecret();
    notify(!!secret?.trim());
  },

  async isModerator(): Promise<boolean> {
    const secret = await storage.getModeratorSecret();
    return !!secret?.trim();
  },

  async getSecret(): Promise<string | null> {
    const secret = await storage.getModeratorSecret();
    return secret?.trim() ? secret : null;
  },

  async login(secret: string): Promise<string | null> {
    const validation = this.validateModeratorSecretInput(secret);
    if (validation) return validation;
    const deviceId = await storage.getDeviceId();
    try {
      await apiRequest(endpoints.chatAddModerator, {
        method: 'POST',
        body: JSON.stringify({ secret: secret.trim(), deviceId }),
        timeoutMs: 10_000,
      });
      await storage.setModeratorSecret(secret.trim());
      notify(true);
      return null;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Помилка з\'єднання';
      if (msg.includes('401') || msg.includes('403')) return 'Невірний пароль';
      return msg;
    }
  },

  async logout(): Promise<void> {
    const deviceId = await storage.getDeviceId();
    const secret = (await storage.getModeratorSecret()) ?? '';
    try {
      await apiRequest(endpoints.chatRemoveModerator, {
        method: 'POST',
        body: JSON.stringify({ secret, deviceId }),
        timeoutMs: 10_000,
      });
    } catch {
      /* still clear local */
    }
    await storage.setModeratorSecret(null);
    notify(false);
  },

  buildMapUrl(theme: 'dark' | 'light' = 'dark'): string {
    // Production embed always targets public map host (Flutter map_tab.dart).
    return `https://neptun.in.ua/?embed=1&theme=${theme}`;
  },

  buildModeratorBootstrapUrl(mapPath: string, secret: string): string {
    const path = mapPath.replace(/^https:\/\/neptun\.in\.ua/i, '') || '/?embed=1&theme=dark';
    const next = encodeURIComponent(path);
    return `https://neptun.in.ua/api/admin/auth/embed?next=${next}`;
  },

  adminInjectScript(secret: string): string {
    const escaped = encodeURIComponent(secret);
    return `window.__ADMIN_SECRET = decodeURIComponent("${escaped}"); true;`;
  },
};

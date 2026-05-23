import { endpoints } from '../config/api';
import { apiRequest } from './apiClient';
import { storage } from './storage';

const JWT_ACCESS = 'jwt_access_token';
const JWT_REFRESH = 'jwt_refresh_token';
const JWT_EXPIRY = 'jwt_token_expiry';

let cachedAccessToken: string | null = null;
let cachedExpiryMs = 0;

function expiryBufferMs(): number {
  return Date.now() + 5 * 60 * 1000;
}

async function readExpiryMs(): Promise<number> {
  const raw = await storage.secureGet(JWT_EXPIRY);
  if (!raw) return 0;
  const ms = Date.parse(raw);
  return Number.isFinite(ms) ? ms : 0;
}

async function saveTokens(accessToken: string, expiresInSec: number, refreshToken?: string | null): Promise<void> {
  const expiresAt = Date.now() + expiresInSec * 1000;
  cachedAccessToken = accessToken;
  cachedExpiryMs = expiresAt;
  await storage.secureSet(JWT_ACCESS, accessToken);
  await storage.secureSet(JWT_EXPIRY, new Date(expiresAt).toISOString());
  if (refreshToken) await storage.secureSet(JWT_REFRESH, refreshToken);
}

/** Mirrors Flutter `AuthService`. */
export const authService = {
  getDeviceId: () => storage.getDeviceId(),

  async hasValidToken(): Promise<boolean> {
    const token = await this.getAccessToken();
    return !!token;
  },

  async getAccessToken(): Promise<string | null> {
    if (cachedAccessToken && cachedExpiryMs > expiryBufferMs()) return cachedAccessToken;

    const access = await storage.secureGet(JWT_ACCESS);
    const expiry = await readExpiryMs();
    if (access && expiry > expiryBufferMs()) {
      cachedAccessToken = access;
      cachedExpiryMs = expiry;
      return access;
    }

    const refreshed = await this.refreshToken();
    return refreshed ? cachedAccessToken : null;
  },

  async getRefreshToken(): Promise<string | null> {
    return storage.secureGet(JWT_REFRESH);
  },

  async login(nickname?: string | null): Promise<boolean> {
    try {
      const deviceId = await storage.getDeviceId();
      const data = await apiRequest<{
        access_token: string;
        refresh_token?: string;
        expires_in: number;
      }>(endpoints.authToken, {
        method: 'POST',
        body: JSON.stringify({ deviceId, nickname: nickname ?? undefined }),
      });
      await saveTokens(data.access_token, data.expires_in, data.refresh_token ?? null);
      return true;
    } catch {
      return false;
    }
  },

  async refreshToken(): Promise<boolean> {
    try {
      const refresh = await storage.secureGet(JWT_REFRESH);
      if (!refresh) return false;

      const data = await apiRequest<{
        access_token: string;
        refresh_token?: string;
        expires_in: number;
      }>(endpoints.authRefresh, {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refresh }),
      });

      await saveTokens(data.access_token, data.expires_in, data.refresh_token ?? refresh);
      return true;
    } catch {
      await this.logout();
      return false;
    }
  },

  async logout(): Promise<void> {
    try {
      const token = cachedAccessToken ?? (await storage.secureGet(JWT_ACCESS));
      if (token) {
        await apiRequest(endpoints.authRevoke, {
          method: 'POST',
          authToken: token,
          timeoutMs: 5000,
        }).catch(() => undefined);
      }
    } catch {
      /* ignore */
    }
    cachedAccessToken = null;
    cachedExpiryMs = 0;
    await storage.secureDelete(JWT_ACCESS);
    await storage.secureDelete(JWT_REFRESH);
    await storage.secureDelete(JWT_EXPIRY);
    await storage.remove('jwt_tokens');
  },

  async getAuthHeaders(): Promise<Record<string, string>> {
    const token = await this.getAccessToken();
    if (token) {
      return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
    }
    return { 'Content-Type': 'application/json' };
  },
};

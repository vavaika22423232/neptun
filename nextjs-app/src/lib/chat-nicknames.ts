import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const NICKNAMES_FILE = path.join(DATA_DIR, 'chat_nicknames.json');

export interface NicknameEntry {
  nickname: string;
  device_id: string;
  registered_at: string;
  hardware_id?: string;
}

export function loadNicknames(): NicknameEntry[] {
  try {
    if (fs.existsSync(NICKNAMES_FILE)) {
      return JSON.parse(fs.readFileSync(NICKNAMES_FILE, 'utf-8'));
    }
  } catch {
    /* empty */
  }
  return [];
}

/** Returns registration timestamp in ms, or null if not found. */
export function getRegistrationTimeMs(deviceId: string): number | null {
  const nicknames = loadNicknames();
  const entry = nicknames.find((n) => n.device_id === deviceId);
  if (!entry?.registered_at) return null;
  const t = new Date(entry.registered_at).getTime();
  return isNaN(t) ? null : t;
}

export const NEW_USER_MS = 24 * 60 * 60 * 1000; // 24 hours

export function isNewUser(deviceId: string): boolean {
  const reg = getRegistrationTimeMs(deviceId);
  if (reg === null) return true; // no nickname = treat as new
  return Date.now() - reg < NEW_USER_MS;
}

/** Get hardware_id for a device from nicknames. Used when creating bans. */
export function getHardwareIdForDevice(deviceId: string): string | undefined {
  const nicknames = loadNicknames();
  const entry = nicknames.find((n) => n.device_id === deviceId);
  return entry?.hardware_id;
}

/** Registered chat nickname for this device (from chat_nicknames.json). */
export function getNicknameForDevice(deviceId: string): string | null {
  const nicknames = loadNicknames();
  const entry = nicknames.find((n) => n.device_id === deviceId);
  const raw = entry?.nickname?.trim();
  return raw && raw.length > 0 ? raw : null;
}

/**
 * Prefer server registry over JWT so chat shows the right name even when the client
 * still sends "Анонім" in the token (old app, refresh without nick, first login).
 */
export function resolveChatDisplayNickname(deviceId: string, jwtNickname: string): string {
  const reg = getNicknameForDevice(deviceId);
  if (reg && reg.length > 0) return reg;
  const j = (jwtNickname || '').trim();
  if (j.length > 0) return j;
  return 'Анонім';
}

/** Get hardware_id for a nickname from nicknames. */
export function getHardwareIdForNickname(nickname: string): string | undefined {
  const nicknames = loadNicknames();
  const entry = nicknames.find(
    (n) => n.nickname?.toLowerCase() === nickname.toLowerCase()
  );
  return entry?.hardware_id;
}

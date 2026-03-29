import fs from 'fs';
import path from 'path';
import { loadChatBans, saveChatBans, type BanEntry } from '@/lib/admin/data';
import { getHardwareIdForDevice, getHardwareIdForNickname } from './chat-nicknames';

const DATA_DIR = process.env.DATA_DIR || '/data';
const VIOLATIONS_FILE = path.join(DATA_DIR, 'chat_violations.json');

export interface ViolationEntry {
  device_id: string;
  nickname: string;
  count: number;
  last_at: string;
}

function loadViolations(): ViolationEntry[] {
  try {
    if (fs.existsSync(VIOLATIONS_FILE)) {
      return JSON.parse(fs.readFileSync(VIOLATIONS_FILE, 'utf-8'));
    }
  } catch {
    /* empty */
  }
  return [];
}

function saveViolations(entries: ViolationEntry[]): void {
  const dir = path.dirname(VIOLATIONS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(VIOLATIONS_FILE, JSON.stringify(entries, null, 2), 'utf-8');
}

const AUTO_BAN_THRESHOLD = 3;
const TEMP_BAN_HOURS = 24;

/** Increment violation count for a user. Returns new count. If >= threshold, adds temp ban. */
export function recordViolation(
  deviceId: string,
  nickname: string
): { count: number; autoBanned: boolean } {
  const violations = loadViolations();
  let entry = violations.find(
    (v) =>
      (deviceId && v.device_id === deviceId) ||
      (nickname && v.nickname?.toLowerCase() === nickname.toLowerCase())
  );
  const now = new Date().toISOString();
  if (!entry) {
    entry = { device_id: deviceId, nickname, count: 0, last_at: now };
    violations.push(entry);
  }
  entry.count += 1;
  entry.last_at = now;
  entry.device_id = deviceId;
  entry.nickname = nickname;
  saveViolations(violations);

  if (entry.count >= AUTO_BAN_THRESHOLD) {
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + TEMP_BAN_HOURS);
    const bans = loadChatBans();
    const hasActiveBan = bans.some(
      (b) =>
        ((b.device_id && b.device_id === deviceId) ||
          (nickname && b.nickname?.toLowerCase() === nickname.toLowerCase())) &&
        (!b.expires_at || new Date(b.expires_at) >= new Date())
    );
    if (!hasActiveBan) {
      const filtered = bans.filter(
        (b) =>
          b.device_id !== deviceId &&
          (!nickname || b.nickname?.toLowerCase() !== nickname.toLowerCase())
      );
      const hardwareId =
        getHardwareIdForDevice(deviceId) || getHardwareIdForNickname(nickname);
      const banEntry: BanEntry = {
        device_id: deviceId,
        nickname,
        reason: `Автоматичний бан за ${entry.count} підтверджених скарг (24 години)`,
        banned_at: now,
        banned_by: 'system',
        expires_at: expiresAt.toISOString(),
        ...(hardwareId && { hardware_id: hardwareId }),
      };
      filtered.push(banEntry);
      saveChatBans(filtered);
      return { count: entry.count, autoBanned: true };
    }
  }
  return { count: entry.count, autoBanned: false };
}

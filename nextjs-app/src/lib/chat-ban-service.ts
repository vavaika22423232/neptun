import { loadChatBans, saveChatBans, type BanEntry, isDangerousPlaceholderBanEntry } from '@/lib/admin/data';
import {
  getHardwareIdForDevice,
  getHardwareIdForNickname,
  getNicknameForDevice,
  loadNicknames,
  type NicknameEntry,
} from '@/lib/chat-nicknames';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_MESSAGES_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_MESSAGES_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

interface ChatBanDependencies {
  loadBans: () => BanEntry[];
  saveBans: (bans: BanEntry[]) => void;
  loadNicknames: () => NicknameEntry[];
  getHardwareIdForDevice: (deviceId: string) => string | undefined;
  getHardwareIdForNickname: (nickname: string) => string | undefined;
  getNicknameForDevice: (deviceId: string) => string | null;
  getRecentDeviceForNickname: (nickname: string) => string | undefined;
}

const defaultDependencies: ChatBanDependencies = {
  loadBans: loadChatBans,
  saveBans: saveChatBans,
  loadNicknames,
  getHardwareIdForDevice,
  getHardwareIdForNickname,
  getNicknameForDevice,
  getRecentDeviceForNickname,
};

export interface BanChatUserInput {
  nickname?: string | null;
  targetDeviceId?: string | null;
  reason?: string | null;
  bannedBy: string;
  defaultReason: string;
}

export interface BanChatUserResult {
  status: 'created' | 'updated' | 'already_banned';
  entry: BanEntry;
  resolvedTargetDevice: string;
  hardwareId?: string;
}

/** Refused ban payload — moderator/API returns 400 */
export class ChatBanRejected extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ChatBanRejected';
  }
}

function normalize(value: string | null | undefined): string {
  return (value || '').trim();
}

function sameText(a: string | null | undefined, b: string | null | undefined): boolean {
  const left = normalize(a).toLowerCase();
  const right = normalize(b).toLowerCase();
  return !!left && !!right && left === right;
}

export function getRecentDeviceForNickname(nickname: string): string | undefined {
  const target = normalize(nickname).toLowerCase();
  if (!target) return undefined;

  for (const filePath of [CHAT_MESSAGES_FILE, FALLBACK_CHAT_MESSAGES_FILE]) {
    try {
      if (!fs.existsSync(filePath)) continue;
      const raw = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(raw) as unknown;
      const messages = Array.isArray(parsed)
        ? parsed
        : parsed && typeof parsed === 'object' && Array.isArray((parsed as { messages?: unknown }).messages)
          ? (parsed as { messages: unknown[] }).messages
          : [];

      for (let i = messages.length - 1; i >= 0; i -= 1) {
        const msg = messages[i];
        if (!msg || typeof msg !== 'object') continue;
        const rec = msg as Record<string, unknown>;
        const msgNickname = normalize(String(rec.userId ?? rec.nickname ?? ''));
        if (msgNickname.toLowerCase() !== target) continue;
        const deviceId = normalize(String(rec.deviceId ?? rec.device_id ?? ''));
        if (deviceId) return deviceId;
      }
    } catch {
      /* try next file */
    }
  }
  return undefined;
}

function findExistingBanIndex(
  bans: BanEntry[],
  nickname: string,
  targetDeviceId: string,
  hardwareId?: string,
): number {
  return bans.findIndex((ban) => {
    const nickMatch = sameText(ban.nickname, nickname);
    const deviceMatch = !!targetDeviceId && ban.device_id === targetDeviceId;
    const hardwareMatch = !!hardwareId && ban.hardware_id === hardwareId;
    return nickMatch || deviceMatch || hardwareMatch;
  });
}

export function banChatUser(
  input: BanChatUserInput,
  deps: ChatBanDependencies = defaultDependencies,
): BanChatUserResult {
  const nickname = normalize(input.nickname);
  const requestedTargetDevice = normalize(input.targetDeviceId);

  if (!nickname && !requestedTargetDevice) {
    throw new Error('nickname or targetDeviceId is required');
  }

  const targetFromRegistry = nickname
    ? deps.loadNicknames().find((entry) => entry.nickname.toLowerCase() === nickname.toLowerCase())
    : undefined;
  const targetFromRecentMessage = nickname ? deps.getRecentDeviceForNickname(nickname) : undefined;
  const resolvedTargetDevice = requestedTargetDevice || targetFromRegistry?.device_id || targetFromRecentMessage || '';
  const hardwareId =
    (resolvedTargetDevice && deps.getHardwareIdForDevice(resolvedTargetDevice)) ||
    (nickname && deps.getHardwareIdForNickname(nickname)) ||
    undefined;
  const displayNickname =
    nickname ||
    (resolvedTargetDevice ? deps.getNicknameForDevice(resolvedTargetDevice) : null) ||
    'Анонім';

  const bans = deps.loadBans();
  const existingIndex = findExistingBanIndex(
    bans,
    nickname,
    resolvedTargetDevice,
    hardwareId,
  );

  if (existingIndex >= 0) {
    const existing = bans[existingIndex];
    let enriched = false;
    if (resolvedTargetDevice && !existing.device_id) {
      existing.device_id = resolvedTargetDevice;
      enriched = true;
    }
    if (displayNickname && isDangerousPlaceholderBanEntry(existing.nickname, existing.device_id, existing.hardware_id)) {
      existing.nickname = displayNickname;
      enriched = true;
    }
    if (hardwareId && !existing.hardware_id) {
      existing.hardware_id = hardwareId;
      enriched = true;
    }
    if (enriched) {
      deps.saveBans(bans);
    }
    return {
      status: enriched ? 'updated' : 'already_banned',
      entry: existing,
      resolvedTargetDevice,
      hardwareId,
    };
  }

  if (isDangerousPlaceholderBanEntry(displayNickname, resolvedTargetDevice, hardwareId)) {
    throw new ChatBanRejected(
      'Неможливо забанити загальний нік «Анонім» без прив\'язки до пристрою — це заблокує всіх гостей чату.',
    );
  }

  const entry: BanEntry = {
    device_id: resolvedTargetDevice,
    nickname: displayNickname,
    reason: normalize(input.reason) || input.defaultReason,
    banned_at: new Date().toISOString(),
    banned_by: input.bannedBy,
    ...(hardwareId && { hardware_id: hardwareId }),
  };

  bans.push(entry);
  deps.saveBans(bans);

  return {
    status: 'created',
    entry,
    resolvedTargetDevice,
    hardwareId,
  };
}

export interface UnbanChatUserInput {
  nickname?: string | null;
  deviceId?: string | null;
  hardwareId?: string | null;
}

export function unbanChatUser(
  input: string | UnbanChatUserInput,
  deps: ChatBanDependencies = defaultDependencies,
): number {
  const normalized =
    typeof input === 'string'
      ? { nickname: input }
      : {
          nickname: input.nickname,
          deviceId: input.deviceId,
          hardwareId: input.hardwareId,
        };
  const nickname = normalize(normalized.nickname);
  const deviceId = normalize(normalized.deviceId);
  const hardwareId = normalize(normalized.hardwareId);

  if (!nickname && !deviceId && !hardwareId) {
    throw new Error('nickname, deviceId or hardwareId is required');
  }

  const bans = deps.loadBans();
  const filtered = bans.filter((ban) => {
    const nickMatch = sameText(ban.nickname, nickname);
    const deviceMatch = !!deviceId && ban.device_id === deviceId;
    const hardwareMatch = !!hardwareId && ban.hardware_id === hardwareId;
    return !(nickMatch || deviceMatch || hardwareMatch);
  });
  deps.saveBans(filtered);
  return bans.length - filtered.length;
}

export function listChatBans(
  deps: ChatBanDependencies = defaultDependencies,
  query = '',
): BanEntry[] {
  const q = normalize(query).toLowerCase();
  const bans = deps.loadBans();
  const filtered = q
    ? bans.filter((ban) =>
        [
          ban.nickname,
          ban.device_id,
          ban.hardware_id,
          ban.reason,
          ban.banned_by,
        ].some((value) => String(value || '').toLowerCase().includes(q)),
      )
    : bans;

  return [...filtered].sort((a, b) => {
    const at = Date.parse(a.banned_at || '') || 0;
    const bt = Date.parse(b.banned_at || '') || 0;
    return bt - at;
  });
}

export type MassUnbanMode = 'all' | 'placeholder_ambiguous' | 'expired';

/**
 * Remove many ban rows at once. Returns how many were removed.
 * - all: empty ban list
 * - placeholder_ambiguous: rows that only targeted generic nick «Анонім» without device/hardware
 * - expired: rows past expires_at
 */
export function massUnbanChatBans(
  mode: MassUnbanMode,
  deps: ChatBanDependencies = defaultDependencies,
): { removed: number; remaining: number } {
  const bans = deps.loadBans();
  const now = new Date();
  let next: BanEntry[];

  if (mode === 'all') {
    next = [];
  } else if (mode === 'placeholder_ambiguous') {
    next = bans.filter(
      (b) =>
        !isDangerousPlaceholderBanEntry(b.nickname, b.device_id ?? '', b.hardware_id),
    );
  } else {
    next = bans.filter((b) => {
      if (!b.expires_at) return true;
      return new Date(b.expires_at) >= now;
    });
  }

  const removed = bans.length - next.length;
  deps.saveBans(next);
  return { removed, remaining: next.length };
}

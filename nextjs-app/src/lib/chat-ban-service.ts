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
  collectDevicesForNickname: (nickname: string) => string[];
}

const defaultDependencies: ChatBanDependencies = {
  loadBans: loadChatBans,
  saveBans: saveChatBans,
  loadNicknames,
  getHardwareIdForDevice,
  getHardwareIdForNickname,
  getNicknameForDevice,
  getRecentDeviceForNickname,
  collectDevicesForNickname,
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

function readChatMessageRecords(): Record<string, unknown>[] {
  for (const filePath of [CHAT_MESSAGES_FILE, FALLBACK_CHAT_MESSAGES_FILE]) {
    try {
      if (!fs.existsSync(filePath)) continue;
      const raw = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(raw) as unknown;
      if (Array.isArray(parsed)) return parsed as Record<string, unknown>[];
      if (
        parsed &&
        typeof parsed === 'object' &&
        Array.isArray((parsed as { messages?: unknown }).messages)
      ) {
        return (parsed as { messages: Record<string, unknown>[] }).messages;
      }
    } catch {
      /* try next file */
    }
  }
  return [];
}

/** All device_ids that posted under this display nickname (newest first). */
export function collectDevicesForNickname(nickname: string): string[] {
  const target = normalize(nickname).toLowerCase();
  if (!target) return [];

  const seen = new Set<string>();
  const ordered: string[] = [];
  const messages = readChatMessageRecords();

  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const rec = messages[i];
    if (!rec || typeof rec !== 'object') continue;
    const msgNickname = normalize(String(rec.userId ?? rec.nickname ?? '')).toLowerCase();
    if (msgNickname !== target) continue;
    const deviceId = normalize(String(rec.deviceId ?? rec.device_id ?? ''));
    if (!deviceId || seen.has(deviceId)) continue;
    seen.add(deviceId);
    ordered.push(deviceId);
  }
  return ordered;
}

export function getRecentDeviceForNickname(nickname: string): string | undefined {
  return collectDevicesForNickname(nickname)[0];
}

function findExistingBanIndex(
  bans: BanEntry[],
  nickname: string,
  targetDeviceId: string,
  hardwareId?: string,
): number {
  return bans.findIndex((ban) => {
    if (hardwareId && ban.hardware_id === hardwareId) return true;
    if (targetDeviceId && ban.device_id === targetDeviceId) return true;
    // Upgrade legacy nickname-only row when we now know the device_id.
    if (targetDeviceId && !ban.device_id && sameText(ban.nickname, nickname)) return true;
    // Nickname-only rows (legacy) — do not collapse different devices under one nick.
    if (!targetDeviceId && !ban.device_id && sameText(ban.nickname, nickname)) return true;
    return false;
  });
}

function upsertBanEntry(
  bans: BanEntry[],
  input: {
    nickname: string;
    deviceId: string;
    hardwareId?: string;
    reason: string;
    bannedBy: string;
  },
): { status: 'created' | 'updated' | 'already_banned'; entry: BanEntry } {
  const existingIndex = findExistingBanIndex(
    bans,
    input.nickname,
    input.deviceId,
    input.hardwareId,
  );

  if (existingIndex >= 0) {
    const existing = bans[existingIndex];
    let enriched = false;
    if (input.deviceId && !existing.device_id) {
      existing.device_id = input.deviceId;
      enriched = true;
    }
    if (
      input.nickname &&
      isDangerousPlaceholderBanEntry(existing.nickname, existing.device_id, existing.hardware_id)
    ) {
      existing.nickname = input.nickname;
      enriched = true;
    }
    if (input.hardwareId && !existing.hardware_id) {
      existing.hardware_id = input.hardwareId;
      enriched = true;
    }
    return {
      status: enriched ? 'updated' : 'already_banned',
      entry: existing,
    };
  }

  const entry: BanEntry = {
    device_id: input.deviceId,
    nickname: input.nickname,
    reason: input.reason,
    banned_at: new Date().toISOString(),
    banned_by: input.bannedBy,
    ...(input.hardwareId && { hardware_id: input.hardwareId }),
  };
  bans.push(entry);
  return { status: 'created', entry };
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
  const devicesFromChat = nickname ? deps.collectDevicesForNickname(nickname) : [];
  const resolvedTargetDevice =
    requestedTargetDevice ||
    targetFromRegistry?.device_id ||
    devicesFromChat[0] ||
    '';
  const hardwareId =
    (resolvedTargetDevice && deps.getHardwareIdForDevice(resolvedTargetDevice)) ||
    (nickname && deps.getHardwareIdForNickname(nickname)) ||
    undefined;
  const displayNickname =
    nickname ||
    (resolvedTargetDevice ? deps.getNicknameForDevice(resolvedTargetDevice) : null) ||
    'Анонім';
  const reason = normalize(input.reason) || input.defaultReason;

  if (isDangerousPlaceholderBanEntry(displayNickname, resolvedTargetDevice, hardwareId)) {
    throw new ChatBanRejected(
      'Неможливо забанити загальний нік «Анонім» без прив\'язки до пристрою — це заблокує всіх гостей чату.',
    );
  }

  const deviceIdsToBan = new Set<string>();
  if (resolvedTargetDevice) deviceIdsToBan.add(resolvedTargetDevice);
  for (const id of devicesFromChat) deviceIdsToBan.add(id);

  if (deviceIdsToBan.size === 0 && !hardwareId) {
    if (isDangerousPlaceholderBanEntry(displayNickname, '', undefined)) {
      throw new ChatBanRejected(
        'Неможливо забанити загальний нік «Анонім» без прив\'язки до пристрою — це заблокує всіх гостей чату.',
      );
    }
    deviceIdsToBan.add('');
  }

  const bans = deps.loadBans();
  let primary: BanEntry | null = null;
  let primaryDevice = resolvedTargetDevice;
  let overallStatus: BanChatUserResult['status'] = 'already_banned';

  for (const deviceId of deviceIdsToBan) {
    const hw =
      (deviceId && deps.getHardwareIdForDevice(deviceId)) ||
      (deviceId === resolvedTargetDevice ? hardwareId : undefined);
    const nick =
      deviceId && deps.getNicknameForDevice(deviceId)
        ? deps.getNicknameForDevice(deviceId)!
        : displayNickname;
    const result = upsertBanEntry(bans, {
      nickname: nick,
      deviceId,
      hardwareId: hw,
      reason,
      bannedBy: input.bannedBy,
    });
    if (!primary) {
      primary = result.entry;
      primaryDevice = deviceId;
      overallStatus = result.status;
    } else if (result.status === 'created') {
      overallStatus = 'created';
    } else if (result.status === 'updated' && overallStatus === 'already_banned') {
      overallStatus = 'updated';
    }
  }

  deps.saveBans(bans);

  return {
    status: overallStatus,
    entry: primary!,
    resolvedTargetDevice: primaryDevice,
    hardwareId:
      (primaryDevice && deps.getHardwareIdForDevice(primaryDevice)) || hardwareId,
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

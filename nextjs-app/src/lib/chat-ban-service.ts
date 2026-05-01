import { loadChatBans, saveChatBans, type BanEntry } from '@/lib/admin/data';
import {
  getHardwareIdForDevice,
  getHardwareIdForNickname,
  getNicknameForDevice,
  loadNicknames,
  type NicknameEntry,
} from '@/lib/chat-nicknames';

interface ChatBanDependencies {
  loadBans: () => BanEntry[];
  saveBans: (bans: BanEntry[]) => void;
  loadNicknames: () => NicknameEntry[];
  getHardwareIdForDevice: (deviceId: string) => string | undefined;
  getHardwareIdForNickname: (nickname: string) => string | undefined;
  getNicknameForDevice: (deviceId: string) => string | null;
}

const defaultDependencies: ChatBanDependencies = {
  loadBans: loadChatBans,
  saveBans: saveChatBans,
  loadNicknames,
  getHardwareIdForDevice,
  getHardwareIdForNickname,
  getNicknameForDevice,
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

function normalize(value: string | null | undefined): string {
  return (value || '').trim();
}

function findExistingBanIndex(
  bans: BanEntry[],
  nickname: string,
  targetDeviceId: string,
): number {
  return bans.findIndex((ban) => {
    const nickMatch =
      !!nickname &&
      ban.nickname.toLowerCase() === nickname.toLowerCase();
    const deviceMatch = !!targetDeviceId && ban.device_id === targetDeviceId;
    return nickMatch || deviceMatch;
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
  const resolvedTargetDevice = requestedTargetDevice || targetFromRegistry?.device_id || '';
  const hardwareId =
    (resolvedTargetDevice && deps.getHardwareIdForDevice(resolvedTargetDevice)) ||
    (nickname && deps.getHardwareIdForNickname(nickname)) ||
    undefined;
  const displayNickname =
    nickname ||
    (resolvedTargetDevice ? deps.getNicknameForDevice(resolvedTargetDevice) : null) ||
    'Анонім';

  const bans = deps.loadBans();
  const existingIndex = findExistingBanIndex(bans, nickname, resolvedTargetDevice);

  if (existingIndex >= 0) {
    const existing = bans[existingIndex];
    let enriched = false;
    if (resolvedTargetDevice && !existing.device_id) {
      existing.device_id = resolvedTargetDevice;
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

export function unbanChatUser(nickname: string, deps: ChatBanDependencies = defaultDependencies): number {
  const normalizedNickname = normalize(nickname);
  if (!normalizedNickname) {
    throw new Error('nickname is required');
  }

  const bans = deps.loadBans();
  const filtered = bans.filter(
    (ban) => ban.nickname.toLowerCase() !== normalizedNickname.toLowerCase(),
  );
  deps.saveBans(filtered);
  return bans.length - filtered.length;
}

export function listChatBans(deps: ChatBanDependencies = defaultDependencies): BanEntry[] {
  return deps.loadBans();
}

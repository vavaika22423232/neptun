import assert from 'node:assert/strict';

import {
  banChatUser,
  listChatBans,
  massUnbanChatBans,
  unbanChatUser,
  ChatBanRejected,
} from '../chat-ban-service';
import type { BanEntry } from '../admin/data';
import type { NicknameEntry } from '../chat-nicknames';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function createDeps(
  seedBans: BanEntry[] = [],
  nicknames: NicknameEntry[] = [],
  recentDevicesByNickname: Record<string, string> = {},
) {
  let bans = [...seedBans];
  return {
    loadBans: () => bans,
    saveBans: (next: BanEntry[]) => {
      bans = [...next];
    },
    loadNicknames: () => nicknames,
    getHardwareIdForDevice: (deviceId: string) =>
      nicknames.find((entry) => entry.device_id === deviceId)?.hardware_id,
    getHardwareIdForNickname: (nickname: string) =>
      nicknames.find((entry) => entry.nickname.toLowerCase() === nickname.toLowerCase())?.hardware_id,
    getNicknameForDevice: (deviceId: string) =>
      nicknames.find((entry) => entry.device_id === deviceId)?.nickname || null,
    getRecentDeviceForNickname: (nickname: string) =>
      recentDevicesByNickname[nickname.toLowerCase()],
    collectDevicesForNickname: (nickname: string) => {
      const id = recentDevicesByNickname[nickname.toLowerCase()];
      return id ? [id] : [];
    },
  };
}

test('banChatUser resolves nickname registry to device and hardware', () => {
  const deps = createDeps([], [
    {
      nickname: 'Pilot',
      device_id: 'device-1',
      registered_at: '2026-04-29T00:00:00.000Z',
      hardware_id: 'hardware-1',
    },
  ]);

  const result = banChatUser(
    {
      nickname: 'pilot',
      bannedBy: 'moderator-1',
      defaultReason: 'rules',
    },
    deps,
  );

  assert.equal(result.status, 'created');
  assert.equal(result.entry.device_id, 'device-1');
  assert.equal(result.entry.hardware_id, 'hardware-1');
  assert.equal(result.entry.banned_by, 'moderator-1');
  assert.equal(listChatBans(deps).length, 1);
});

test('banChatUser enriches an existing nickname ban without duplicating it', () => {
  const deps = createDeps(
    [
      {
        device_id: '',
        nickname: 'Pilot',
        reason: 'old',
        banned_at: '2026-04-29T00:00:00.000Z',
      },
    ],
    [
      {
        nickname: 'Pilot',
        device_id: 'device-1',
        registered_at: '2026-04-29T00:00:00.000Z',
        hardware_id: 'hardware-1',
      },
    ],
  );

  const result = banChatUser(
    {
      nickname: 'Pilot',
      bannedBy: 'admin',
      defaultReason: 'rules',
    },
    deps,
  );

  const bans = listChatBans(deps);
  assert.equal(result.status, 'updated');
  assert.equal(bans.length, 1);
  assert.equal(bans[0].device_id, 'device-1');
  assert.equal(bans[0].hardware_id, 'hardware-1');
});

test('banChatUser resolves nickname from recent chat messages when registry is missing', () => {
  const deps = createDeps([], [], { pilot: 'device-from-message' });

  const result = banChatUser(
    {
      nickname: 'Pilot',
      bannedBy: 'moderator-1',
      defaultReason: 'rules',
    },
    deps,
  );

  assert.equal(result.status, 'created');
  assert.equal(result.entry.nickname, 'Pilot');
  assert.equal(result.entry.device_id, 'device-from-message');
});

test('unbanChatUser removes matching nickname case-insensitively', () => {
  const deps = createDeps([
    {
      device_id: 'device-1',
      nickname: 'Pilot',
      reason: 'rules',
      banned_at: '2026-04-29T00:00:00.000Z',
    },
  ]);

  const removed = unbanChatUser('pilot', deps);

  assert.equal(removed, 1);
  assert.deepEqual(listChatBans(deps), []);
});

test('unbanChatUser removes matching concrete device without relying on nickname', () => {
  const deps = createDeps([
    {
      device_id: 'device-1',
      nickname: 'Анонім',
      reason: 'rules',
      banned_at: '2026-04-29T00:00:00.000Z',
      hardware_id: 'hardware-1',
    },
  ]);

  const removed = unbanChatUser({ deviceId: 'device-1' }, deps);

  assert.equal(removed, 1);
  assert.deepEqual(listChatBans(deps), []);
});

test('listChatBans searches nickname, device, hardware and reason', () => {
  const deps = createDeps([
    {
      device_id: 'device-1',
      nickname: 'Pilot',
      reason: 'spam',
      banned_at: '2026-04-29T00:00:00.000Z',
      hardware_id: 'hardware-1',
    },
    {
      device_id: 'device-2',
      nickname: 'Scout',
      reason: 'flood',
      banned_at: '2026-04-30T00:00:00.000Z',
      hardware_id: 'hardware-2',
    },
  ]);

  assert.equal(listChatBans(deps, 'hardWARE-2')[0]?.nickname, 'Scout');
  assert.equal(listChatBans(deps, 'spam')[0]?.nickname, 'Pilot');
});

test('banChatUser rejects placeholder Анонім ban without device or hardware', () => {
  assert.throws(
    () =>
      banChatUser(
        { nickname: 'Анонім', bannedBy: 'mod-1', defaultReason: 'rules' },
        createDeps([], []),
      ),
    ChatBanRejected,
  );
});

test('massUnbanChatBans placeholder_ambiguous removes only ambiguous rows', () => {
  const deps = createDeps(
    [
      {
        device_id: '',
        nickname: 'Анонім',
        reason: 'bad',
        banned_at: '2026-05-01T00:00:00.000Z',
      },
      {
        device_id: 'dev-x',
        nickname: 'Pilot',
        reason: 'spam',
        banned_at: '2026-05-01T00:00:00.000Z',
      },
    ],
    [],
  );
  const r = massUnbanChatBans('placeholder_ambiguous', deps);
  assert.equal(r.removed, 1);
  assert.equal(r.remaining, 1);
  assert.equal(listChatBans(deps)[0]?.nickname, 'Pilot');
});

test('massUnbanChatBans expired removes only expired', () => {
  const past = new Date(Date.now() - 86400000).toISOString();
  const future = new Date(Date.now() + 86400000).toISOString();
  const deps = createDeps(
    [
      {
        device_id: 'a',
        nickname: 'Old',
        reason: 'x',
        banned_at: '2026-05-01T00:00:00.000Z',
        expires_at: past,
      },
      {
        device_id: 'b',
        nickname: 'Still',
        reason: 'y',
        banned_at: '2026-05-01T00:00:00.000Z',
        expires_at: future,
      },
      {
        device_id: 'c',
        nickname: 'Perm',
        reason: 'z',
        banned_at: '2026-05-01T00:00:00.000Z',
      },
    ],
    [],
  );
  const r = massUnbanChatBans('expired', deps);
  assert.equal(r.removed, 1);
  assert.equal(r.remaining, 2);
});

test('banChatUser allows nickname-only ban when device unknown (legacy app)', () => {
  const deps = createDeps([], [], {});
  const result = banChatUser(
    {
      nickname: 'UnknownGuest',
      bannedBy: 'mod-1',
      defaultReason: 'rules',
    },
    deps,
  );
  assert.equal(result.status, 'created');
  assert.equal(result.entry.nickname, 'UnknownGuest');
  assert.equal(result.entry.device_id, '');
});

test('banChatUser bans every device_id seen under the same nickname in chat', () => {
  const deps = createDeps(
    [],
    [],
    { spamer: 'device-a' },
  );
  (deps as ReturnType<typeof createDeps> & {
    collectDevicesForNickname: (n: string) => string[];
  }).collectDevicesForNickname = () => ['device-a', 'device-b'];

  const result = banChatUser(
    {
      nickname: 'Spamer',
      bannedBy: 'mod-1',
      defaultReason: 'rules',
    },
    deps,
  );
  assert.equal(result.status, 'created');
  assert.equal(listChatBans(deps).length, 2);
  assert.ok(listChatBans(deps).some((b) => b.device_id === 'device-a'));
  assert.ok(listChatBans(deps).some((b) => b.device_id === 'device-b'));
});

test('massUnbanChatBans all clears list', () => {
  const deps = createDeps(
    [
      {
        device_id: 'a',
        nickname: 'A',
        reason: 'x',
        banned_at: '2026-05-01T00:00:00.000Z',
      },
    ],
    [],
  );
  const r = massUnbanChatBans('all', deps);
  assert.equal(r.removed, 1);
  assert.equal(r.remaining, 0);
});

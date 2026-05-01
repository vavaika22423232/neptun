import assert from 'node:assert/strict';

import { banChatUser, listChatBans, unbanChatUser } from '../chat-ban-service';
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

function createDeps(seedBans: BanEntry[] = [], nicknames: NicknameEntry[] = []) {
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

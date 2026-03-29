import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { loadChatBans, saveChatBans, isModeratorDevice, type BanEntry } from '@/lib/admin/data';

const DATA_DIR = process.env.DATA_DIR || '/data';
const NICKNAMES_FILE = path.join(DATA_DIR, 'chat_nicknames.json');

interface NicknameEntry {
  nickname: string;
  device_id: string;
  registered_at: string;
}

function loadNicknames(): NicknameEntry[] {
  try {
    if (fs.existsSync(NICKNAMES_FILE)) {
      return JSON.parse(fs.readFileSync(NICKNAMES_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

/**
 * POST /api/chat/ban-user
 * Ban a user from chat (moderator action).
 * Requires moderator deviceId in body.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { nickname, deviceId, reason } = body;

    // Auth: only moderators can ban
    if (!deviceId || !isModeratorDevice(deviceId)) {
      return NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 });
    }

    if (!nickname) {
      return NextResponse.json({ error: 'Відсутній нікнейм' }, { status: 400 });
    }

    const bans = loadChatBans();

    // Check if already banned by nickname
    if (bans.some((b) => b.nickname.toLowerCase() === nickname.toLowerCase())) {
      return NextResponse.json({ status: 'ok', message: 'Already banned' });
    }

    // Lookup device_id from registered nicknames
    const nicknames = loadNicknames();
    const target = nicknames.find((n) => n.nickname.toLowerCase() === nickname.toLowerCase());
    const targetDeviceId = target?.device_id || '';

    // Also check if already banned by device_id to prevent duplicates
    if (targetDeviceId && bans.some((b) => b.device_id === targetDeviceId)) {
      return NextResponse.json({ status: 'ok', message: 'Already banned (by device)' });
    }

    const entry: BanEntry = {
      device_id: targetDeviceId,
      nickname,
      reason: reason || 'Порушення правил',
      banned_at: new Date().toISOString(),
      banned_by: deviceId,
    };

    bans.push(entry);
    saveChatBans(bans);
    console.log(`[CHAT] Banned: ${nickname} (device: ${targetDeviceId}) by ${deviceId}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Ban error:', err);
    return NextResponse.json({ error: 'Помилка блокування' }, { status: 500 });
  }
}

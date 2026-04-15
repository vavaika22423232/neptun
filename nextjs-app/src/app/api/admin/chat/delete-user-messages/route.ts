import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { invalidateChatCache } from '@/app/api/chat/messages/route';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

function resolveChatFile(): string {
  return fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
}

/**
 * POST /api/admin/chat/delete-user-messages
 * Delete all chat messages from a user (admin action).
 * Body: { nickname, deviceId } — at least one required.
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const body = await request.json();
    const { nickname, deviceId } = body;

    const nicknameMatch = (nickname || '').trim().toLowerCase();
    const deviceIdMatch = (deviceId || '').trim();

    if (!nicknameMatch && !deviceIdMatch) {
      return NextResponse.json({ error: 'Потрібен nickname або deviceId' }, { status: 400 });
    }

    const filePath = resolveChatFile();
    let messages: Array<Record<string, unknown>> = [];

    try {
      if (fs.existsSync(filePath)) {
        const raw = await fsp.readFile(filePath, 'utf-8');
        const data = JSON.parse(raw);
        messages = Array.isArray(data) ? data : (data.messages || []) as Array<Record<string, unknown>>;
      }
    } catch {
      return NextResponse.json({ error: 'Не вдалось прочитати чат' }, { status: 500 });
    }

    const toDelete = new Set<string>();
    for (const m of messages) {
      const msgDeviceId = (m.deviceId || m.device_id || '').toString();
      const msgUserId = (m.userId || m.nickname || '').toString().toLowerCase();
      const matchDevice = deviceIdMatch && msgDeviceId === deviceIdMatch;
      const matchNickname = nicknameMatch && msgUserId === nicknameMatch;
      if (matchDevice || matchNickname) {
        toDelete.add((m.id || '').toString());
      }
    }

    const remaining = messages.filter((m) => !toDelete.has((m.id || '').toString()));
    const deletedCount = toDelete.size;

    if (deletedCount > 0) {
      const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
      await fsp.writeFile(tmp, JSON.stringify(remaining, null, 2), 'utf-8');
      await fsp.rename(tmp, filePath);

      invalidateChatCache();
      for (const id of toDelete) {
        broadcastSSE({ type: 'delete_message', data: { messageId: id } });
      }
    }

    console.log(`[CHAT] Admin deleted ${deletedCount} messages for user ${nickname || deviceId}`);
    return NextResponse.json({ status: 'ok', deleted: deletedCount });
  } catch (err) {
    console.error('[CHAT] Admin delete-user-messages error:', err);
    return NextResponse.json({ error: 'Помилка видалення' }, { status: 500 });
  }
}

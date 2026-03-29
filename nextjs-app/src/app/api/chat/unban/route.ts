import { NextResponse } from 'next/server';
import { loadChatBans, saveChatBans, isModeratorDevice } from '@/lib/admin/data';

/**
 * POST /api/chat/unban
 * Unban a user from chat (moderator action).
 * Requires moderator deviceId in body.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { nickname, deviceId } = body;

    // Auth: only moderators can unban
    if (!deviceId || !isModeratorDevice(deviceId)) {
      return NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 });
    }

    if (!nickname) {
      return NextResponse.json({ error: 'Missing nickname' }, { status: 400 });
    }

    const bans = loadChatBans();
    const filtered = bans.filter((b) => b.nickname.toLowerCase() !== nickname.toLowerCase());
    saveChatBans(filtered);

    console.log(`[CHAT] Unbanned: ${nickname} by ${deviceId}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

import { NextResponse } from 'next/server';
import { loadChatBans, isModeratorDevice } from '@/lib/admin/data';

/**
 * GET /api/chat/ban-list?deviceId=xxx
 * Get list of banned users with details (moderator action).
 * Requires moderator deviceId as query param.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const deviceId = searchParams.get('deviceId') || '';

  // Auth: only moderators can view ban list
  if (!deviceId || !isModeratorDevice(deviceId)) {
    return NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 });
  }

  const bans = loadChatBans();
  return NextResponse.json({
    banned: bans.map((b) => b.nickname),
    details: bans,
  });
}

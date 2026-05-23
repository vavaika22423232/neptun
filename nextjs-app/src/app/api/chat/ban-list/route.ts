import { NextResponse } from 'next/server';
import { isModeratorDevice } from '@/lib/admin/data';
import { listChatBans } from '@/lib/chat-ban-service';
import { requireModeratorAuth } from '@/lib/moderator-auth';

/**
 * GET /api/chat/ban-list?q=
 * Moderator or admin only (JWT moderator device or admin session).
 */
export async function GET(request: Request) {
  const mod = await requireModeratorAuth(request);
  if (!mod.ok) return mod.response;

  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q') || '';

  const bans = listChatBans(undefined, query);
  return NextResponse.json({
    banned: bans.map((b) => b.nickname),
    details: bans.map((b) => ({
      nickname: b.nickname,
      reason: b.reason,
      banned_at: b.banned_at,
    })),
    query,
  });
}

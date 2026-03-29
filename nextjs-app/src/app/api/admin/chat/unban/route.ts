import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadChatBans, saveChatBans } from '@/lib/admin/data';

/**
 * POST /api/admin/chat/unban
 * Unban a user (admin — uses X-Auth-Secret or session).
 * Body: { nickname }
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const body = await request.json();
    const nickname = (body.nickname || '').trim();

    if (!nickname) {
      return NextResponse.json({ error: 'Missing nickname' }, { status: 400 });
    }

    const bans = loadChatBans();
    const filtered = bans.filter((b) => b.nickname.toLowerCase() !== nickname.toLowerCase());
    saveChatBans(filtered);

    console.log(`[CHAT] Admin unbanned: ${nickname}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Admin unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

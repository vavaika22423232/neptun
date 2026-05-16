import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { listChatBans } from '@/lib/chat-ban-service';

/**
 * GET /api/admin/chat/ban-list
 * Get list of banned users (admin — uses X-Auth-Secret or session).
 */
export async function GET(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  const query = new URL(request.url).searchParams.get('q') || '';
  const bans = listChatBans(undefined, query);
  return NextResponse.json({
    banned: bans.map((b) => b.nickname),
    details: bans,
    query,
  });
}

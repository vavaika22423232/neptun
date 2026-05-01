import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { listChatBans } from '@/lib/chat-ban-service';

/**
 * GET /api/admin/chat/ban-list
 * Get list of banned users (admin — uses X-Auth-Secret or session).
 */
export async function GET() {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  const bans = listChatBans();
  return NextResponse.json({
    banned: bans.map((b) => b.nickname),
    details: bans,
  });
}

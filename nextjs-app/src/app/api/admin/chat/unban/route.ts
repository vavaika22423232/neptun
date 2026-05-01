import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { ChatUnbanUserSchema } from '@/lib/api-schemas';
import { unbanChatUser } from '@/lib/chat-ban-service';

/**
 * POST /api/admin/chat/unban
 * Unban a user (admin — uses X-Auth-Secret or session).
 * Body: { nickname }
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const parsed = ChatUnbanUserSchema.pick({ nickname: true }).safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const { nickname } = parsed.data;

    unbanChatUser(nickname);

    console.log(`[CHAT] Admin unbanned: ${nickname}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Admin unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

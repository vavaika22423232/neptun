import { NextResponse } from 'next/server';
import { ChatModeratorBanUserSchema } from '@/lib/api-schemas';
import { banChatUser, ChatBanRejected } from '@/lib/chat-ban-service';
import { requireModeratorAuth } from '@/lib/moderator-auth';

/**
 * POST /api/chat/ban-user
 * Ban a user from chat (moderator or admin only).
 */
export async function POST(request: Request) {
  try {
    const mod = await requireModeratorAuth(request);
    if (!mod.ok) return mod.response;

    const parsed = ChatModeratorBanUserSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const { nickname, targetDeviceId, reason } = parsed.data;

    const bannedBy = mod.via === 'admin' ? 'admin-app' : mod.identity.deviceId;

    const result = banChatUser({
      nickname,
      targetDeviceId,
      reason,
      bannedBy,
      defaultReason: 'Порушення правил',
    });

    if (result.status !== 'created') {
      if (result.status === 'updated') {
        console.log(`[CHAT] Ban enriched: ${result.entry.nickname}`);
      }
      return NextResponse.json({
        status: 'ok',
        message: result.status === 'updated' ? 'Ban updated' : 'Already banned',
      });
    }

    console.log(`[CHAT] User banned by ${mod.via}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    if (err instanceof ChatBanRejected) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    console.error('[CHAT] Ban error:', err);
    return NextResponse.json({ error: 'Помилка блокування' }, { status: 500 });
  }
}

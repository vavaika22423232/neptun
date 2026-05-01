import { NextResponse } from 'next/server';
import { isModeratorDevice } from '@/lib/admin/data';
import { ChatModeratorBanUserSchema } from '@/lib/api-schemas';
import { banChatUser } from '@/lib/chat-ban-service';

/**
 * POST /api/chat/ban-user
 * Ban a user from chat (moderator action).
 * Body: { nickname?, deviceId: moderatorDeviceId, targetDeviceId?, reason? }
 * — deviceId is the moderator's device (must be in chat_moderators.json).
 * — targetDeviceId is the offender's device when known (e.g. from chat message); required for reliable ban if nickname is not in chat_nicknames.json.
 */
export async function POST(request: Request) {
  try {
    const parsed = ChatModeratorBanUserSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const {
      nickname,
      deviceId: modDeviceId,
      targetDeviceId,
      reason,
    } = parsed.data;

    if (!modDeviceId || !isModeratorDevice(modDeviceId)) {
      return NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 });
    }

    const result = banChatUser({
      nickname,
      targetDeviceId,
      reason,
      bannedBy: modDeviceId,
      defaultReason: 'Порушення правил',
    });

    if (result.status !== 'created') {
      if (result.status === 'updated') {
        console.log(`[CHAT] Ban enriched: ${result.entry.nickname} (device: ${result.entry.device_id})`);
      }
      return NextResponse.json({
        status: 'ok',
        message: result.status === 'updated' ? 'Ban updated' : 'Already banned',
      });
    }

    console.log(
      `[CHAT] Banned: ${result.entry.nickname} (device: ${result.resolvedTargetDevice}) by ${modDeviceId}`,
    );
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Ban error:', err);
    return NextResponse.json({ error: 'Помилка блокування' }, { status: 500 });
  }
}

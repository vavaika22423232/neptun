import { NextResponse } from 'next/server';
import { isModeratorDevice } from '@/lib/admin/data';
import { ChatUnbanUserSchema } from '@/lib/api-schemas';
import { unbanChatUser } from '@/lib/chat-ban-service';

/**
 * POST /api/chat/unban
 * Unban a user from chat (moderator action).
 * Requires moderator deviceId in body.
 */
export async function POST(request: Request) {
  try {
    const parsed = ChatUnbanUserSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const { nickname, deviceId, targetDeviceId, hardwareId } = parsed.data;

    // Auth: only moderators can unban
    if (!deviceId || !isModeratorDevice(deviceId)) {
      return NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 });
    }
    if (!nickname && !targetDeviceId && !hardwareId) {
      return NextResponse.json(
        { error: 'nickname, targetDeviceId or hardwareId is required' },
        { status: 400 },
      );
    }

    const removed = unbanChatUser({
      nickname,
      deviceId: targetDeviceId,
      hardwareId,
    });

    console.log(`[CHAT] Unbanned: ${nickname || targetDeviceId || hardwareId} by ${deviceId}`);
    return NextResponse.json({ status: 'ok', removed });
  } catch (err) {
    console.error('[CHAT] Unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

import { NextResponse } from 'next/server';
import { ChatUnbanUserSchema } from '@/lib/api-schemas';
import { unbanChatUser } from '@/lib/chat-ban-service';
import { requireModeratorAuth } from '@/lib/moderator-auth';

/**
 * POST /api/chat/unban
 * Moderator or admin only.
 */
export async function POST(request: Request) {
  try {
    const mod = await requireModeratorAuth(request);
    if (!mod.ok) return mod.response;

    const parsed = ChatUnbanUserSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const { nickname, targetDeviceId, hardwareId } = parsed.data;

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

    const actor =
      mod.via === 'moderator' ? mod.identity.deviceId.slice(0, 8) : 'admin';
    console.log(`[CHAT] Unbanned by ${actor}`);
    return NextResponse.json({ status: 'ok', removed });
  } catch (err) {
    console.error('[CHAT] Unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

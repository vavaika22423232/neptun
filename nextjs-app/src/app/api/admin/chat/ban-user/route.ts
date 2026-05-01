import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { ChatAdminBanUserSchema } from '@/lib/api-schemas';
import { banChatUser } from '@/lib/chat-ban-service';

/**
 * POST /api/admin/chat/ban-user
 * Ban a user from chat (admin action — uses session or X-Auth-Secret).
 * Body: { nickname, deviceId, reason? }
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const parsed = ChatAdminBanUserSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }
    const { nickname, deviceId: targetDeviceId, reason } = parsed.data;

    const result = banChatUser({
      nickname,
      targetDeviceId,
      reason,
      bannedBy: 'admin',
      defaultReason: 'Порушення правил (адмін)',
    });

    if (result.status !== 'created') {
      if (result.status === 'updated') {
        console.log(`[CHAT] Admin ban enriched: ${result.entry.nickname} (device: ${result.entry.device_id})`);
      }
      return NextResponse.json({
        status: 'ok',
        message: result.status === 'updated' ? 'Ban updated' : 'Already banned',
      });
    }

    console.log(`[CHAT] Admin banned: ${result.entry.nickname} (device: ${result.resolvedTargetDevice})`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Admin ban error:', err);
    return NextResponse.json({ error: 'Помилка блокування' }, { status: 500 });
  }
}

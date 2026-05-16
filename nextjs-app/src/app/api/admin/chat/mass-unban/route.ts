import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { ChatMassUnbanSchema } from '@/lib/api-schemas';
import { massUnbanChatBans } from '@/lib/chat-ban-service';

/**
 * POST /api/admin/chat/mass-unban
 * Admin only (session or X-Auth-Secret).
 *
 * Body: { mode, confirm: true }
 * - all — розблокувати всіх (очистити chat_bans.json)
 * - placeholder_ambiguous — лише «небезпечні» рядки (нік-заглушка без device/hardware)
 * - expired — лише прострочені тимчасові бани
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const parsed = ChatMassUnbanSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }

    const { mode } = parsed.data;
    const result = massUnbanChatBans(mode);

    console.log(`[CHAT] Mass unban mode=${mode} removed=${result.removed} remaining=${result.remaining}`);

    return NextResponse.json({
      status: 'ok',
      mode,
      removed: result.removed,
      remaining: result.remaining,
    });
  } catch (err) {
    console.error('[CHAT] Mass unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

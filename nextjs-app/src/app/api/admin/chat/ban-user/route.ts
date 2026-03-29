import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadChatBans, saveChatBans, type BanEntry } from '@/lib/admin/data';
import { getHardwareIdForDevice, getHardwareIdForNickname } from '@/lib/chat-nicknames';

/**
 * POST /api/admin/chat/ban-user
 * Ban a user from chat (admin action — uses session or X-Auth-Secret).
 * Body: { nickname, deviceId, reason? }
 */
export async function POST(request: Request) {
  const authRes = await requireAdminAuth();
  if (authRes) return authRes;

  try {
    const body = await request.json();
    const { nickname, deviceId: targetDeviceId, reason } = body;

    const nicknameToBan = (nickname || '').trim();
    const deviceIdToBan = (targetDeviceId || '').trim();

    if (!nicknameToBan && !deviceIdToBan) {
      return NextResponse.json({ error: 'Потрібен nickname або deviceId' }, { status: 400 });
    }

    const bans = loadChatBans();

    if (nicknameToBan && bans.some((b) => b.nickname.toLowerCase() === nicknameToBan.toLowerCase())) {
      return NextResponse.json({ status: 'ok', message: 'Already banned' });
    }
    if (deviceIdToBan && bans.some((b) => b.device_id === deviceIdToBan)) {
      return NextResponse.json({ status: 'ok', message: 'Already banned (by device)' });
    }

    const hardwareId =
      (deviceIdToBan && getHardwareIdForDevice(deviceIdToBan)) ||
      (nicknameToBan && getHardwareIdForNickname(nicknameToBan));

    const entry: BanEntry = {
      device_id: deviceIdToBan,
      nickname: nicknameToBan || 'Анонім',
      reason: reason || 'Порушення правил (адмін)',
      banned_at: new Date().toISOString(),
      banned_by: 'admin',
      ...(hardwareId && { hardware_id: hardwareId }),
    };

    bans.push(entry);
    saveChatBans(bans);
    console.log(`[CHAT] Admin banned: ${entry.nickname} (device: ${deviceIdToBan})`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Admin ban error:', err);
    return NextResponse.json({ error: 'Помилка блокування' }, { status: 500 });
  }
}

import { NextResponse } from 'next/server';
import { isBanned } from '@/lib/admin/data';
import { requireChatAuth } from '@/lib/chat-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

/**
 * POST /api/chat/check-ban
 * Returns ban status for the authenticated device only (no enumeration).
 */
export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:chat:check_ban:${ipRedisTag(ip)}`,
      120,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'chat_check_ban' });
      return NextResponse.json({ banned: false }, { status: 429 });
    }

    const auth = requireChatAuth(request);
    if (auth instanceof Response) return auth;

    let hardwareId: string | undefined;
    try {
      const body = await request.json();
      if (typeof body?.hardwareId === 'string') hardwareId = body.hardwareId.slice(0, 128);
    } catch {
      /* optional body */
    }

    const ban = isBanned(auth.deviceId, auth.nickname, hardwareId);

    return NextResponse.json({
      banned: !!ban,
      reason: ban?.reason || null,
    });
  } catch (err) {
    console.error('[CHAT] Check-ban error:', err);
    return NextResponse.json({ banned: false });
  }
}

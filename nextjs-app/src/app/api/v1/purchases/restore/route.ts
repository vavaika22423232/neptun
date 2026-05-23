import { NextResponse } from 'next/server';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/purchases/restore
 * Client sends deviceId after store restore; server returns current entitlements.
 */
export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:purchase:restore:${ipRedisTag(ip)}`,
      20,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'purchase_restore' });
      return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
    }

    const body = await request.json();
    const auth = await requireDeviceAuthFromJson(request, body);
    if (!auth.ok) return auth.response;
    const deviceId = auth.deviceId;

    const entitlements = await resolveEntitlementsForDevice(deviceId);
    return NextResponse.json({ restored: entitlements.isPro, entitlements });
  } catch (e) {
    console.error('[v1/purchases/restore]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

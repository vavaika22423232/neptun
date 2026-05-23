import { NextResponse } from 'next/server';
import { verifyAndBindPurchase } from '@/lib/monetization/verify-purchase';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:purchase:verify:${ipRedisTag(ip)}`,
      30,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'purchase_google_verify' });
      return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
    }

    const body = await request.json();
    const auth = await requireDeviceAuthFromJson(request, body);
    if (!auth.ok) return auth.response;
    const deviceId = auth.deviceId;

    const result = await verifyAndBindPurchase({
      deviceId,
      productId: body?.productId ?? body?.product_id,
      purchaseToken: body?.purchaseToken ?? body?.purchase_token,
      source: 'google_play',
      platform: body?.platform,
      appVersion: body?.appVersion,
      expiresAt: body?.expiresAt ?? null,
      originalTransactionId: body?.originalTransactionId ?? null,
    });

    if (!result.ok) {
      return NextResponse.json(
        { ok: false, valid: false, reason: result.reason, pending: result.reason === 'pending', transient: result.reason === 'transient', error: result.reason },
        { status: result.reason === 'bad_input' ? 400 : 200 },
      );
    }

    const entitlements = await resolveEntitlementsForDevice(deviceId);
    return NextResponse.json({ ok: true, valid: true, plan: result.plan, entitlements });
  } catch (e) {
    console.error('[v1/purchases/google/verify]', e);
    return NextResponse.json({ valid: false, transient: true, error: 'internal' }, { status: 500 });
  }
}

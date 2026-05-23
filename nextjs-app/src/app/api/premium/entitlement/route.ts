import { NextResponse } from 'next/server';
import {
  assertPremiumPurchase,
  type PremiumAssertResult,
} from '@/lib/iap-assert-premium';
import {
  getEntitlement,
  saveEntitlement,
  deleteEntitlement,
  updateLastVerified,
  ENTITLEMENT_REVERIFY_MS,
} from '@/lib/premium-entitlement-db';
import { requireDeviceAuth, requireDeviceAuthFromJson } from '@/lib/device-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';
import { z } from 'zod';

export const dynamic = 'force-dynamic';

const PremiumEntitlementPostSchema = z.object({
  deviceId: z.string().min(8).max(128).optional(),
  device_id: z.string().min(8).max(128).optional(),
  productId: z.string().min(1).max(128),
  purchaseToken: z.string().min(1).max(8192),
  source: z.string().max(32).optional(),
});

function mapAssertToEntitled(r: PremiumAssertResult): boolean {
  return r.kind === 'valid';
}

/**
 * GET /api/premium/entitlement?deviceId=...
 * Legacy entitlement check — requires device JWT.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const auth = requireDeviceAuth(request, url.searchParams.get('deviceId'));
  if (!auth.ok) return auth.response;
  const deviceId = auth.deviceId;

  try {
    const rec = await getEntitlement(deviceId);
    if (!rec) {
      return NextResponse.json({ entitled: false, noBinding: true });
    }

    const last = Date.parse(rec.lastVerifiedAt);
    const fresh =
      Number.isFinite(last) && Date.now() - last < ENTITLEMENT_REVERIFY_MS;

    if (fresh) {
      return NextResponse.json({ entitled: true, cached: true });
    }

    const result = await assertPremiumPurchase(
      rec.productId,
      rec.purchaseToken,
      rec.source === 'app_store' ? 'app_store' : undefined,
    );

    if (result.kind === 'valid') {
      await updateLastVerified(deviceId, new Date().toISOString());
      return NextResponse.json({ entitled: true, cached: false });
    }

    if (result.kind === 'transient' || result.kind === 'misconfigured' || result.kind === 'pending') {
      return NextResponse.json({
        entitled: true,
        stale: true,
        reason: result.kind,
      });
    }

    await deleteEntitlement(deviceId);
    return NextResponse.json({
      entitled: false,
      revoked: true,
      reason: 'purchase_invalid',
    });
  } catch (e) {
    console.error('[PREMIUM_ENTITLEMENT] GET error:', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

/**
 * POST /api/premium/entitlement
 * Legacy bind — requires device JWT + rate limit. Prefer v1 purchase verify.
 */
export async function POST(request: Request) {
  const ip = getClientIp(request);
  const allowed = await redisFixedWindowAllow(
    `rl:legacy:entitlement:${ipRedisTag(ip)}`,
    20,
    3600,
    false,
  );
  if (!allowed) {
    logSecurityEvent('rate_limit_hit', { route: 'legacy_premium_entitlement' });
    return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
  }

  try {
    const body = await request.json();
    const auth = await requireDeviceAuthFromJson(request, body);
    if (!auth.ok) return auth.response;
    const deviceId = auth.deviceId;

    const parsed = PremiumEntitlementPostSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json({ error: 'missing_fields' }, { status: 400 });
    }

    const { productId, purchaseToken, source } = parsed.data;

    const result = await assertPremiumPurchase(
      productId,
      purchaseToken,
      source === 'app_store' ? 'app_store' : undefined,
    );

    if (result.kind === 'misconfigured') {
      return NextResponse.json({ ok: false, error: 'server_misconfigured' }, { status: 503 });
    }
    if (result.kind === 'transient') {
      return NextResponse.json({ ok: false, transient: true }, { status: 503 });
    }
    if (result.kind === 'pending') {
      return NextResponse.json({ ok: false, pending: true }, { status: 200 });
    }
    if (!mapAssertToEntitled(result)) {
      return NextResponse.json({ ok: false, entitled: false }, { status: 200 });
    }

    const now = new Date().toISOString();
    const existing = await getEntitlement(deviceId);
    const registeredAt = existing?.registeredAt || now;
    await saveEntitlement(deviceId, {
      productId,
      purchaseToken,
      source: source === 'app_store' ? 'app_store' : 'google_play',
      lastVerifiedAt: now,
      registeredAt,
    });

    return NextResponse.json({ ok: true, entitled: true });
  } catch (e) {
    console.error('[PREMIUM_ENTITLEMENT] POST error:', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

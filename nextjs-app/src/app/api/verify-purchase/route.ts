import { NextResponse } from 'next/server';
import {
  assertPremiumPurchase,
  type PremiumAssertResult,
} from '@/lib/iap-assert-premium';
import { LegacyVerifyPurchaseSchema } from '@/lib/api-schemas';
import { requireChatAuth } from '@/lib/chat-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

/**
 * POST /api/verify-purchase
 * Legacy receipt probe — requires device JWT + rate limit.
 * Prefer POST /api/v1/purchases/{apple|google}/verify for new clients.
 */
export async function POST(request: Request) {
  const ip = getClientIp(request);
  const allowed = await redisFixedWindowAllow(
    `rl:legacy:verify:${ipRedisTag(ip)}`,
    20,
    3600,
    false,
  );
  if (!allowed) {
    logSecurityEvent('rate_limit_hit', { route: 'legacy_verify_purchase' });
    return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
  }

  const auth = requireChatAuth(request);
  if (auth instanceof Response) return auth;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const parsed = LegacyVerifyPurchaseSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
  }

  const { productId, purchaseToken, source } = parsed.data;

  try {
    const r = await assertPremiumPurchase(productId, purchaseToken, source);
    return mapAssertToResponse(r);
  } catch (err) {
    console.error('[PURCHASE] Verify error:', err);
    return NextResponse.json(
      { valid: false, transient: true, error: 'internal' },
      { status: 503 },
    );
  }
}

function mapAssertToResponse(r: PremiumAssertResult): NextResponse {
  switch (r.kind) {
    case 'valid':
      return NextResponse.json({ valid: true });
    case 'invalid':
      return NextResponse.json({ valid: false }, { status: 200 });
    case 'pending':
      return NextResponse.json({ valid: false, pending: true });
    case 'misconfigured':
      return NextResponse.json({ valid: false, error: 'server_misconfigured' }, { status: 503 });
    case 'transient':
      return NextResponse.json({ valid: false, transient: true, error: 'transient' }, { status: 503 });
    default:
      return NextResponse.json({ valid: false }, { status: 200 });
  }
}

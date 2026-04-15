import { NextResponse } from 'next/server';
import {
  assertPremiumPurchase,
  type PremiumAssertResult,
} from '@/lib/iap-assert-premium';

/**
 * POST /api/verify-purchase
 * Verify in-app purchase via Google Play or App Store API.
 */
export async function POST(request: Request) {
  let body: { productId?: string; purchaseToken?: string; source?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { productId, purchaseToken, source } = body;

  if (!productId || !purchaseToken) {
    return NextResponse.json(
      { error: 'Missing productId or purchaseToken' },
      { status: 400 }
    );
  }

  console.log(`[PURCHASE] Verify: ${productId} from ${source || 'unknown'}`);

  try {
    const r = await assertPremiumPurchase(productId, purchaseToken, source);
    return mapAssertToResponse(r);
  } catch (err) {
    console.error('[PURCHASE] Verify error:', err);
    return NextResponse.json(
      { valid: false, transient: true, error: 'internal' },
      { status: 503 }
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
      return NextResponse.json({
        valid: false,
        pending: true,
      });
    case 'misconfigured':
      return NextResponse.json(
        { valid: false, error: 'server_misconfigured' },
        { status: 503 }
      );
    case 'transient':
      return NextResponse.json(
        { valid: false, transient: true, error: 'transient' },
        { status: 503 }
      );
    default:
      return NextResponse.json({ valid: false }, { status: 200 });
  }
}

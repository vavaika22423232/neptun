import { NextResponse } from 'next/server';

/**
 * POST /api/verify-purchase
 * Verify in-app purchase for premium features.
 * Currently auto-validates — integrate with Play/App Store verification APIs later.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { productId, purchaseToken, source } = body;

    if (!productId || !purchaseToken) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    console.log(`[PURCHASE] Verify: ${productId} from ${source || 'unknown'}`);

    // TODO: Verify with Google Play / App Store APIs
    // For now, accept all purchases
    return NextResponse.json({ valid: true });
  } catch (err) {
    console.error('[PURCHASE] Verify error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

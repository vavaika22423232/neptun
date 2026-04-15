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

export const dynamic = 'force-dynamic';

function sanitizeDeviceId(raw: string | null): string | null {
  if (!raw || typeof raw !== 'string') return null;
  const s = raw.trim();
  if (s.length < 8 || s.length > 200) return null;
  if (!/^[\w.-]+$/.test(s)) return null;
  return s;
}

function mapAssertToEntitled(r: PremiumAssertResult): boolean {
  return r.kind === 'valid';
}

/**
 * GET /api/premium/entitlement?deviceId=...
 * Returns whether this device has a server-side Pro binding; re-verifies with Google/Apple if stale.
 */
export async function GET(request: Request) {
  const deviceId = sanitizeDeviceId(new URL(request.url).searchParams.get('deviceId'));
  if (!deviceId) {
    return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });
  }

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
      rec.source === 'app_store' ? 'app_store' : undefined
    );

    if (result.kind === 'valid') {
      await updateLastVerified(deviceId, new Date().toISOString());
      return NextResponse.json({ entitled: true, cached: false });
    }

    if (result.kind === 'transient' || result.kind === 'misconfigured' || result.kind === 'pending') {
      // Do not revoke on transient/pending — keep previous good state
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
 * Body: { deviceId, productId, purchaseToken, source? }
 * Verifies purchase with store, then stores binding for GET re-checks.
 */
export async function POST(request: Request) {
  let body: {
    deviceId?: string;
    productId?: string;
    purchaseToken?: string;
    source?: string;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const deviceId = sanitizeDeviceId(body.deviceId ?? null);
  const productId = typeof body.productId === 'string' ? body.productId.trim() : '';
  const purchaseToken =
    typeof body.purchaseToken === 'string' ? body.purchaseToken.trim() : '';
  const source = typeof body.source === 'string' ? body.source.trim() : '';

  if (!deviceId || !productId || !purchaseToken) {
    return NextResponse.json({ error: 'missing_fields' }, { status: 400 });
  }

  try {
    const result = await assertPremiumPurchase(
      productId,
      purchaseToken,
      source === 'app_store' ? 'app_store' : undefined
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
    if (result.kind !== 'valid') {
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

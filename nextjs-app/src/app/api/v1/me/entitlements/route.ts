import { NextResponse } from 'next/server';
import {
  assertPremiumPurchase,
} from '@/lib/iap-assert-premium';
import {
  deleteStoredEntitlement,
  getStoredEntitlement,
  resolveEntitlementsForDevice,
  updateLastVerified,
  ENTITLEMENT_REVERIFY_MS,
} from '@/lib/monetization/entitlement-store';
import { buildEntitlements } from '@/lib/monetization/plans';
import { requireDeviceAuth } from '@/lib/device-auth';

export const dynamic = 'force-dynamic';

/**
 * GET /api/v1/me/entitlements?deviceId=...
 * Canonical entitlements payload for mobile clients.
 */
export async function GET(request: Request) {
  const deviceIdParam = new URL(request.url).searchParams.get('deviceId');
  const auth = requireDeviceAuth(request, deviceIdParam);
  if (!auth.ok) return auth.response;
  const deviceId = auth.deviceId;

  try {
    const stored = await getStoredEntitlement(deviceId);
    if (!stored) {
      return NextResponse.json(buildEntitlements('free'));
    }

    const last = Date.parse(stored.lastVerifiedAt);
    const fresh = Number.isFinite(last) && Date.now() - last < ENTITLEMENT_REVERIFY_MS;

    if (!fresh) {
      const result = await assertPremiumPurchase(
        stored.productId,
        stored.purchaseToken,
        stored.source === 'app_store' ? 'app_store' : undefined,
      );

      if (result.kind === 'valid') {
        await updateLastVerified(deviceId, new Date().toISOString());
      } else if (result.kind === 'invalid') {
        await deleteStoredEntitlement(deviceId);
        return NextResponse.json(buildEntitlements('free', { status: 'expired' }));
      }
      // transient: keep stored plan
    }

    const entitlements = await resolveEntitlementsForDevice(deviceId);
    return NextResponse.json(entitlements);
  } catch (e) {
    console.error('[v1/me/entitlements]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

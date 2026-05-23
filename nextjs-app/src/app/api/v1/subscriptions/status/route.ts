import { NextResponse } from 'next/server';
import { getStoredEntitlement, resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const auth = await requireAuthenticatedDevice(
    request,
    new URL(request.url).searchParams.get('deviceId'),
  );
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const stored = await getStoredEntitlement(deviceId);
  const entitlements = await resolveEntitlementsForDevice(deviceId);

  return NextResponse.json({
    plan: entitlements.plan,
    status: entitlements.status,
    expiresAt: entitlements.expiresAt,
    productId: stored?.productId ?? null,
    entitlements,
  });
}

import { NextResponse } from 'next/server';
import { ensureUserForDevice, resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const auth = await requireAuthenticatedDevice(request, url.searchParams.get('deviceId'));
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const { userId, createdAt } = await ensureUserForDevice(deviceId);
  const entitlements = await resolveEntitlementsForDevice(deviceId);

  return NextResponse.json({
    userId,
    deviceId,
    createdAt,
    lastSeenAt: new Date().toISOString(),
    entitlements,
  });
}

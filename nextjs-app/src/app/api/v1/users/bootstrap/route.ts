import { NextResponse } from 'next/server';
import { ensureUserForDevice, resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/users/bootstrap
 * Anonymous user + device registration; returns userId + entitlements.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const auth = await requireDeviceAuthFromJson(request, body);
    if (!auth.ok) return auth.response;
    const deviceId = auth.deviceId;

    const { userId, created } = await ensureUserForDevice(deviceId, {
      platform: body?.platform,
      appVersion: body?.appVersion ?? body?.app_version,
      locale: body?.locale ?? 'uk',
    });

    const entitlements = await resolveEntitlementsForDevice(deviceId);

    return NextResponse.json({
      userId,
      deviceId,
      created,
      entitlements,
    });
  } catch (e) {
    console.error('[v1/users/bootstrap]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

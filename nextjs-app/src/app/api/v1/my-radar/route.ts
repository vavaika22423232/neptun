import { NextResponse } from 'next/server';
import { ensureUserForDevice, sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';
import { listMyRadarLocations } from '@/lib/monetization/my-radar-store';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const deviceId = sanitizeDeviceId(new URL(request.url).searchParams.get('deviceId'));
  if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

  const gate = await requireMinPlan(request, deviceId, 'pro');
  if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

  const { userId } = await ensureUserForDevice(deviceId);
  const locations = await listMyRadarLocations(userId);

  return NextResponse.json({
    locations,
    limit: gate.features.myRadarLocationsLimit,
    summary: {
      locationCount: locations.length,
      updatedAt: new Date().toISOString(),
      note: 'За наявними даними NEPTUN; статуси оновлюються з моніторингу.',
    },
  });
}

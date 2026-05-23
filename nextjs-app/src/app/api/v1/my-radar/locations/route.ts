import { NextResponse } from 'next/server';
import {
  createMyRadarLocation,
  listMyRadarLocations,
} from '@/lib/monetization/my-radar-store';
import { ensureUserForDevice, sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const deviceId = sanitizeDeviceId(body?.deviceId ?? body?.device_id);
    if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

    const gate = await requireMinPlan(request, deviceId, 'pro');
    if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

    const { userId } = await ensureUserForDevice(deviceId);
    const existing = await listMyRadarLocations(userId);
    if (existing.length >= gate.features.myRadarLocationsLimit) {
      return NextResponse.json(
        { error: 'limit_reached', limit: gate.features.myRadarLocationsLimit },
        { status: 403 },
      );
    }

    const loc = await createMyRadarLocation(userId, {
      label: String(body?.label ?? 'Локація'),
      type: body?.type ?? 'custom',
      regionId: String(body?.regionId ?? body?.region_id ?? ''),
      cityId: body?.cityId ?? null,
      sortOrder: Number(body?.sortOrder ?? existing.length),
    });

    return NextResponse.json({ location: loc });
  } catch (e) {
    console.error('[v1/my-radar/locations POST]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

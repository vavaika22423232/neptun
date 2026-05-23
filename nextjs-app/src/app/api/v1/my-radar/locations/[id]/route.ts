import { NextResponse } from 'next/server';
import {
  deleteMyRadarLocation,
  updateMyRadarLocation,
} from '@/lib/monetization/my-radar-store';
import { ensureUserForDevice, sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const deviceId = sanitizeDeviceId(body?.deviceId ?? body?.device_id);
    if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

    const gate = await requireMinPlan(request, deviceId, 'pro');
    if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

    const { userId } = await ensureUserForDevice(deviceId);
    const loc = await updateMyRadarLocation(id, userId, {
      label: body?.label,
      type: body?.type,
      regionId: body?.regionId ?? body?.region_id,
      cityId: body?.cityId,
      sortOrder: body?.sortOrder,
    });
    if (!loc) return NextResponse.json({ error: 'not_found' }, { status: 404 });
    return NextResponse.json({ location: loc });
  } catch (e) {
    console.error('[v1/my-radar/locations PATCH]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const url = new URL(request.url);
  const deviceId = sanitizeDeviceId(url.searchParams.get('deviceId'));
  if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

  const gate = await requireMinPlan(request, deviceId, 'pro');
  if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

  const { userId } = await ensureUserForDevice(deviceId);
  const ok = await deleteMyRadarLocation(id, userId);
  if (!ok) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  return NextResponse.json({ ok: true });
}

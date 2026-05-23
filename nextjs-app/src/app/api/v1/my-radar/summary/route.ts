import { NextResponse } from 'next/server';
import { getCurrentAlertsFromRedis } from '@/lib/monetization/alert-history-store';
import { listMyRadarLocations } from '@/lib/monetization/my-radar-store';
import { ensureUserForDevice, sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const deviceId = sanitizeDeviceId(new URL(request.url).searchParams.get('deviceId'));
  if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

  const gate = await requireMinPlan(request, deviceId, 'pro');
  if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

  const { userId } = await ensureUserForDevice(deviceId);
  const locations = await listMyRadarLocations(userId);
  const live = await getCurrentAlertsFromRedis();
  const activeByRegion = new Map(
    live.filter((a) => a.activeAlerts?.length).map((a) => [a.regionId, a]),
  );

  const cards = locations.map((loc) => {
    const alarm = activeByRegion.get(loc.regionId);
    const active = Boolean(alarm?.activeAlerts?.length);
    const types = alarm?.activeAlerts?.map((x) => x.type) ?? [];
    return {
      location: loc,
      status: active ? 'alert' : 'clear',
      activeThreats: types,
      lastUpdate: alarm?.activeAlerts?.[0]?.lastUpdate ?? null,
      severity: active ? 'high' : 'low',
    };
  });

  const alertCount = cards.filter((c) => c.status === 'alert').length;
  const summaryText =
    alertCount > 0
      ? `За наявними даними: тривога в ${alertCount} з ${locations.length} обраних локацій. Інформація оновлюється.`
      : `За наявними даними обрані локації без активної тривоги. Інформація оновлюється.`;

  return NextResponse.json({
    locations: cards,
    summaryText,
    updatedAt: new Date().toISOString(),
    importance: alertCount > 0 ? 'elevated' : 'normal',
  });
}

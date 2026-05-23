import { NextResponse } from 'next/server';
import { listMyRadarLocations } from '@/lib/monetization/my-radar-store';
import { buildDailyReport } from '@/lib/monetization/reports-service';
import { ensureUserForDevice, resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const auth = await requireAuthenticatedDevice(
    request,
    new URL(request.url).searchParams.get('deviceId'),
  );
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const ent = await resolveEntitlementsForDevice(deviceId);
  if (!ent.isPro) {
    return NextResponse.json({ error: 'plan_required', upgradeRequired: 'pro' }, { status: 403 });
  }

  const { userId } = await ensureUserForDevice(deviceId);
  const locations = await listMyRadarLocations(userId);
  const today = new Date().toISOString().slice(0, 10);
  const daily = await buildDailyReport(locations[0]?.regionId ?? null, today);

  return NextResponse.json({
    plan: ent.plan,
    myRadarCount: locations.length,
    dailySnippet: ent.features.dailyReports ? daily.summaryText : null,
    updatedAt: new Date().toISOString(),
  });
}

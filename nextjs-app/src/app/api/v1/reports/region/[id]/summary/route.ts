import { NextResponse } from 'next/server';
import { buildDailyReport, buildWeeklyReport } from '@/lib/monetization/reports-service';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id: regionId } = await params;
  const url = new URL(request.url);
  const auth = await requireAuthenticatedDevice(request, url.searchParams.get('deviceId'));
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const ent = await resolveEntitlementsForDevice(deviceId);
  if (!ent.isPro) {
    return NextResponse.json({ error: 'plan_required', upgradeRequired: 'pro' }, { status: 403 });
  }

  const date = url.searchParams.get('date') ?? new Date().toISOString().slice(0, 10);
  const daily = await buildDailyReport(regionId, date);
  const weekly = ent.features.weeklyReports
    ? await buildWeeklyReport(regionId, url.searchParams.get('week') ?? date)
    : null;

  return NextResponse.json({
    regionId,
    daily,
    weekly,
    plan: ent.plan,
    exportAllowed: ent.features.exportReports,
  });
}

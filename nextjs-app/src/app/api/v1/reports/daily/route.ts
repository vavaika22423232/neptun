import { NextResponse } from 'next/server';
import { buildDailyReport } from '@/lib/monetization/reports-service';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const auth = await requireAuthenticatedDevice(request, url.searchParams.get('deviceId'));
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const ent = await resolveEntitlementsForDevice(deviceId);
  if (!ent.features.dailyReports) {
    return NextResponse.json({ error: 'plan_required', upgradeRequired: 'pro' }, { status: 403 });
  }

  const date = url.searchParams.get('date') ?? new Date().toISOString().slice(0, 10);
  const regionId = url.searchParams.get('region') ?? url.searchParams.get('regionId');
  const report = await buildDailyReport(regionId, date);
  return NextResponse.json({ report, plan: ent.plan });
}

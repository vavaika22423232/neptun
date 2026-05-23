import { NextResponse } from 'next/server';
import { aggregateRegionStatsDaily } from '@/lib/monetization/alert-history-store';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { historyCutoffIso, requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

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
  if (!ent.features.advancedAnalytics) {
    return NextResponse.json({ error: 'plan_required', upgradeRequired: 'pro_plus' }, { status: 403 });
  }

  const from = url.searchParams.get('from') ?? historyCutoffIso(ent.features.historyDays);
  const to = url.searchParams.get('to') ?? new Date().toISOString();
  if (from < historyCutoffIso(ent.features.historyDays)) {
    return NextResponse.json({ error: 'history_range_locked', maxDays: ent.features.historyDays }, { status: 403 });
  }

  const stats = await aggregateRegionStatsDaily(regionId, from, to);
  return NextResponse.json({ regionId, from, to, stats, plan: ent.plan });
}

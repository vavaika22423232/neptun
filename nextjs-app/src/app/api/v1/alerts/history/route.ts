import { NextResponse } from 'next/server';
import { listAlertEvents } from '@/lib/monetization/alert-history-store';
import { historyCutoffIso, requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const deviceIdParam = url.searchParams.get('deviceId');
  const auth = await requireAuthenticatedDevice(request, deviceIdParam);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status });
  }

  const ent = await resolveEntitlementsForDevice(auth.deviceId);
  const cutoff = historyCutoffIso(ent.features.historyDays);
  const from = url.searchParams.get('from');
  const to = url.searchParams.get('to') ?? new Date().toISOString();
  const fromIso = from && from >= cutoff ? from : cutoff;

  if (from && from < cutoff) {
    return NextResponse.json(
      {
        error: 'history_range_locked',
        maxDays: ent.features.historyDays,
        cutoff,
        upgradeRequired: ent.plan === 'free' ? 'pro' : ent.plan === 'pro' ? 'pro_plus' : 'max',
      },
      { status: 403 },
    );
  }

  const regionId = url.searchParams.get('region') ?? url.searchParams.get('regionId') ?? undefined;
  const type = url.searchParams.get('type') ?? undefined;

  const events = await listAlertEvents({ regionId, fromIso, toIso: to, type, limit: 300 });

  return NextResponse.json({
    events,
    from: fromIso,
    to,
    maxDays: ent.features.historyDays,
    plan: ent.plan,
  });
}

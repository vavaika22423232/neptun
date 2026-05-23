import { NextResponse } from 'next/server';
import { getAlertEvent } from '@/lib/monetization/alert-history-store';
import { resolveEntitlementsForDevice } from '@/lib/monetization/entitlement-store';
import { historyCutoffIso, requireAuthenticatedDevice } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = await requireAuthenticatedDevice(
    request,
    new URL(request.url).searchParams.get('deviceId'),
  );
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const deviceId = auth.deviceId;

  const ent = await resolveEntitlementsForDevice(deviceId);
  const event = await getAlertEvent(id);
  if (!event) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const cutoff = historyCutoffIso(ent.features.historyDays);
  if (event.startedAt < cutoff) {
    return NextResponse.json({ error: 'history_range_locked', maxDays: ent.features.historyDays }, { status: 403 });
  }

  return NextResponse.json({ event, plan: ent.plan });
}

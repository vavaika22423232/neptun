import { NextResponse } from 'next/server';
import { getCurrentAlertsFromRedis } from '@/lib/monetization/alert-history-store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const alarms = await getCurrentAlertsFromRedis();
  const active = alarms.filter((a) => a.activeAlerts?.length > 0);
  return NextResponse.json({
    alarms: active,
    updatedAt: new Date().toISOString(),
    disclaimer: 'За наявними даними; інформація оновлюється.',
  });
}

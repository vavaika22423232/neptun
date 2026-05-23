import { NextResponse } from 'next/server';
import { listTelegramTemplates } from '@/lib/monetization/telegram-admin';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';
import { sanitizeDeviceId } from '@/lib/monetization/entitlement-store';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const deviceId = sanitizeDeviceId(new URL(request.url).searchParams.get('deviceId'));
  if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

  const gate = await requireMinPlan(request, deviceId, 'max');
  if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

  return NextResponse.json({ templates: listTelegramTemplates() });
}

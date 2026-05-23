import { NextResponse } from 'next/server';
import { generateTelegramSummary, type TelegramTemplateId } from '@/lib/monetization/telegram-admin';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';
import { sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const deviceId = sanitizeDeviceId(body?.deviceId ?? body?.device_id);
    if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

    const allowed = await redisFixedWindowAllow(`rl:tg_admin:${deviceId}`, 20, 3600, false);
    if (!allowed) {
      return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
    }

    const gate = await requireMinPlan(request, deviceId, 'max');
    if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

    const text = generateTelegramSummary({
      templateId: (body?.templateId ?? 'short_regions') as TelegramTemplateId,
      regionId: body?.regionId,
      regionName: body?.regionName,
      language: body?.language,
      style: body?.style,
      activeAlerts: body?.activeAlerts,
      threatTypes: body?.threatTypes,
      periodLabel: body?.periodLabel,
    });

    return NextResponse.json({ text, disclaimer: 'За наявними даними; орієнтовно.' });
  } catch (e) {
    console.error('[telegram/generate-summary]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

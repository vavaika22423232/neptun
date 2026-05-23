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

    const allowed = await redisFixedWindowAllow(`rl:tg_export:${deviceId}`, 10, 3600, false);
    if (!allowed) return NextResponse.json({ error: 'rate_limited' }, { status: 429 });

    const gate = await requireMinPlan(request, deviceId, 'max');
    if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

    const text = generateTelegramSummary({
      templateId: (body?.templateId ?? 'channel_post') as TelegramTemplateId,
      regionId: body?.regionId,
      regionName: body?.regionName,
      language: body?.language ?? 'uk',
      style: body?.style ?? 'telegram_channel',
      activeAlerts: body?.activeAlerts,
      threatTypes: body?.threatTypes,
      periodLabel: body?.periodLabel,
    });

    return NextResponse.json({
      format: 'telegram_card',
      text,
      mimeType: 'text/plain',
      filename: `neptun-summary-${Date.now()}.txt`,
      disclaimer: 'За наявними даними; орієнтовно.',
    });
  } catch (e) {
    console.error('[telegram/export-card]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

import { NextResponse } from 'next/server';
import {
  createNotificationRule,
  listNotificationRules,
} from '@/lib/monetization/notification-rules-store';
import { ensureUserForDevice, sanitizeDeviceId } from '@/lib/monetization/entitlement-store';
import { requireMinPlan } from '@/lib/monetization/require-entitlement';

export const dynamic = 'force-dynamic';

async function userIdFromRequest(request: Request, body?: Record<string, unknown>): Promise<string | null> {
  const url = new URL(request.url);
  const deviceId = sanitizeDeviceId(
    url.searchParams.get('deviceId') ?? String(body?.deviceId ?? body?.device_id ?? ''),
  );
  if (!deviceId) return null;
  const { userId } = await ensureUserForDevice(deviceId);
  return userId;
}

export async function GET(request: Request) {
  const deviceId = sanitizeDeviceId(new URL(request.url).searchParams.get('deviceId'));
  if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

  const gate = await requireMinPlan(request, deviceId, 'pro');
  if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

  const { userId } = await ensureUserForDevice(deviceId);
  const rules = await listNotificationRules(userId);
  return NextResponse.json({ rules, limit: gate.features.notificationRulesLimit });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const deviceId = sanitizeDeviceId(body?.deviceId ?? body?.device_id);
    if (!deviceId) return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });

    const gate = await requireMinPlan(request, deviceId, 'pro');
    if (!gate.ok) return NextResponse.json({ error: gate.error }, { status: gate.status });

    const { userId } = await ensureUserForDevice(deviceId);
    const existing = await listNotificationRules(userId);
    if (existing.length >= gate.features.notificationRulesLimit) {
      return NextResponse.json({ error: 'limit_reached', limit: gate.features.notificationRulesLimit }, { status: 403 });
    }

    const rule = await createNotificationRule(userId, {
      regionIds: body?.regionIds ?? body?.region_ids ?? [],
      cityIds: body?.cityIds ?? [],
      threatTypes: body?.threatTypes ?? body?.threat_types ?? [],
      quietModeEnabled: body?.quietModeEnabled,
      quietModeStart: body?.quietModeStart,
      quietModeEnd: body?.quietModeEnd,
      criticalOverrideEnabled: body?.criticalOverrideEnabled,
      dedupeWindowMinutes: body?.dedupeWindowMinutes,
    });

    return NextResponse.json({ rule });
  } catch (e) {
    console.error('[v1/notification-rules POST]', e);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}

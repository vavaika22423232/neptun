/**
 * Server-side push gating — plan, quiet mode, dedupe, critical override.
 * Integrate before FCM send when alarm/threat pushes are routed through the API.
 */

import { resolveEntitlementsForDevice, sanitizeDeviceId } from './entitlement-store';
import { listNotificationRules, type NotificationRuleRecord } from './notification-rules-store';

export type PushGateInput = {
  deviceId: string;
  regionId?: string;
  threatType?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  isCritical?: boolean;
  dedupeKey?: string;
};

export type PushGateResult = { allow: true } | { allow: false; reason: string };

const DEDUPE_PREFIX = 'monetization:push_dedupe:';
const DEDUPE_DEFAULT_MIN = 5;

function inQuietWindow(rule: NotificationRuleRecord, now: Date): boolean {
  if (!rule.quietModeEnabled || !rule.quietModeStart || !rule.quietModeEnd) return false;
  const [sh, sm] = rule.quietModeStart.split(':').map(Number);
  const [eh, em] = rule.quietModeEnd.split(':').map(Number);
  const mins = now.getHours() * 60 + now.getMinutes();
  const start = sh * 60 + (sm || 0);
  const end = eh * 60 + (em || 0);
  if (start <= end) return mins >= start && mins < end;
  return mins >= start || mins < end;
}

export async function shouldDeliverPush(input: PushGateInput): Promise<PushGateResult> {
  const deviceId = sanitizeDeviceId(input.deviceId);
  if (!deviceId) return { allow: false, reason: 'bad_device' };

  const ent = await resolveEntitlementsForDevice(deviceId);
  if (!ent.features.smartNotifications) {
    return { allow: true };
  }

  const { ensureUserForDevice } = await import('./entitlement-store');
  const { userId } = await ensureUserForDevice(deviceId);
  const userRules = await listNotificationRules(userId);
  const enabled = userRules.filter((r) => r.enabled);
  if (enabled.length === 0) {
    return { allow: true };
  }

  const now = new Date();
  const critical = input.isCritical || input.severity === 'critical';

  for (const rule of enabled) {
    if (inQuietWindow(rule, now)) {
      if (critical && rule.criticalOverrideEnabled) continue;
      return { allow: false, reason: 'quiet_mode' };
    }

    if (rule.regionIds.length && input.regionId && !rule.regionIds.includes(input.regionId)) {
      return { allow: false, reason: 'region_filtered' };
    }

    if (rule.threatTypes.length && input.threatType && !rule.threatTypes.includes(input.threatType) && !rule.threatTypes.includes('all')) {
      return { allow: false, reason: 'threat_filtered' };
    }
  }

  const dedupeMin = enabled[0]?.dedupeWindowMinutes ?? DEDUPE_DEFAULT_MIN;
  if (input.dedupeKey) {
    const { getRedis } = await import('@/lib/redis');
    const key = `${DEDUPE_PREFIX}${deviceId}:${input.dedupeKey}`;
    const ok = await getRedis().set(key, '1', 'EX', dedupeMin * 60, 'NX');
    if (ok !== 'OK') return { allow: false, reason: 'deduped' };
  }

  return { allow: true };
}

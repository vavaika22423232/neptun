import { persistentStorage } from '../../../services/persistentStorage';

function parseTime(raw: string, fallbackHour: number, fallbackMinute: number): number {
  const parts = raw.split(':');
  const h = Number(parts[0]);
  const m = Number(parts[1] ?? 0);
  if (!Number.isFinite(h) || h < 0 || h > 23) return fallbackHour * 60 + fallbackMinute;
  if (!Number.isFinite(m) || m < 0 || m > 59) return fallbackHour * 60 + fallbackMinute;
  return h * 60 + m;
}

function isWithinQuietWindow(nowMinutes: number, startMinutes: number, endMinutes: number): boolean {
  if (startMinutes === endMinutes) return false;
  if (startMinutes > endMinutes) {
    return nowMinutes >= startMinutes || nowMinutes < endMinutes;
  }
  return nowMinutes >= startMinutes && nowMinutes < endMinutes;
}

/** Flutter `_shouldAllowByQuietHours` — returns true when notification may be shown. */
export function shouldAllowByQuietHours(isCritical: boolean): boolean {
  const enabled = persistentStorage.getBoolean('quiet_hours_enabled', false);
  if (!enabled) return true;
  const allowCritical = persistentStorage.getBoolean('quiet_hours_allow_critical', true);
  if (isCritical && allowCritical) return true;

  const startRaw = persistentStorage.getString('quiet_hours_start') ?? '22:00';
  const endRaw = persistentStorage.getString('quiet_hours_end') ?? '07:00';
  const start = parseTime(startRaw, 22, 0);
  const end = parseTime(endRaw, 7, 0);
  const now = new Date();
  const current = now.getHours() * 60 + now.getMinutes();
  return !isWithinQuietWindow(current, start, end);
}

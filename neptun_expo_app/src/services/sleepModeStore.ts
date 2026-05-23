import { storage } from './storage';

export type SleepModeSettings = {
  enabled: boolean;
  startHour: number;
  startMinute: number;
  endHour: number;
  endMinute: number;
  allowRockets: boolean;
  allowDrones: boolean;
  allowAllClear: boolean;
};

let cached: SleepModeSettings = {
  enabled: false,
  startHour: 23,
  startMinute: 0,
  endHour: 7,
  endMinute: 0,
  allowRockets: true,
  allowDrones: false,
  allowAllClear: false,
};

export function getSleepModeCached(): SleepModeSettings {
  return cached;
}

export async function hydrateSleepMode(): Promise<void> {
  cached = await storage.getJson('sleep_mode_settings_v1', cached);
}

export async function saveSleepModeSettings(patch: Partial<SleepModeSettings>): Promise<void> {
  cached = { ...cached, ...patch };
  await storage.setJson('sleep_mode_settings_v1', cached);
}

function isInSleepTime(settings: SleepModeSettings): boolean {
  if (!settings.enabled) return false;
  const now = new Date();
  const current = now.getHours() * 60 + now.getMinutes();
  const start = settings.startHour * 60 + settings.startMinute;
  const end = settings.endHour * 60 + settings.endMinute;
  return start > end ? current >= start || current < end : current >= start && current < end;
}

export function shouldBlockSleepNotification(body: string): boolean {
  if (!isInSleepTime(cached)) return false;
  const lower = body.toLowerCase();
  const isRocket =
    lower.includes('ракет') ||
    lower.includes('балістичн') ||
    lower.includes('калібр') ||
    lower.includes('кинджал') ||
    lower.includes('каб') ||
    lower.includes('касет');
  const isDrone = lower.includes('бпла') || lower.includes('дрон') || lower.includes('шахед');
  const isAllClear = lower.includes('відбій');
  if (isRocket && cached.allowRockets) return false;
  if (isDrone && cached.allowDrones) return false;
  if (isAllClear && cached.allowAllClear) return false;
  if (!isRocket && !isDrone && !isAllClear && cached.allowRockets) return false;
  return true;
}

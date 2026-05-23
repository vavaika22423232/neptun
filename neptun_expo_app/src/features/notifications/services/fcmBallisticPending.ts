import { ballisticAlertService } from '../../map/services/ballisticAlertService';
import { persistentStorage } from '../../../services/persistentStorage';
import type { FcmData } from './fcmMessagePipeline';

const ALERT_KEY = 'pending_ballistic_alert';
const REGION_KEY = 'pending_ballistic_region';
const TIME_KEY = 'pending_ballistic_time';
const MAX_AGE_MS = 5 * 60_000;

function str(v: unknown): string {
  return v == null ? '' : String(v);
}

/**
 * Flutter background FCM handler — stash ballistic state for cold start.
 * Call only when app is backgrounded/killed (`foreground === false`).
 */
export function recordBallisticFromFcmIfNeeded(data: FcmData): void {
  const body = str(data.body);
  const threatType = str(data.threat_type);
  const alarmState = str(data.alarm_state);
  const region = str(data.region);
  const lowerBody = body.toLowerCase();
  const lowerThreat = threatType.toLowerCase();

  const isBallisticThreat =
    lowerBody.includes('балістик') ||
    lowerBody.includes('балистик') ||
    lowerThreat.includes('ballistic') ||
    lowerThreat.includes('балістик');

  const isBallisticAllClear =
    (lowerBody.includes('відбій') && lowerBody.includes('балістик')) ||
    (alarmState === 'ended' && isBallisticThreat);

  const now = String(Date.now());

  if (isBallisticAllClear) {
    persistentStorage.setString(ALERT_KEY, 'all_clear');
    persistentStorage.setString(REGION_KEY, region);
    persistentStorage.setString(TIME_KEY, now);
    return;
  }

  if (isBallisticThreat) {
    persistentStorage.setString(ALERT_KEY, 'threat');
    persistentStorage.setString(REGION_KEY, region);
    persistentStorage.setString(TIME_KEY, now);
  }
}

/** Flutter `NotificationService.checkPendingBallisticAlert`. */
export function consumePendingBallisticAlert(): void {
  const pendingAlert = persistentStorage.getString(ALERT_KEY);
  const pendingRegion = persistentStorage.getString(REGION_KEY) ?? '';
  const pendingTime = Number(persistentStorage.getString(TIME_KEY) ?? '0');

  persistentStorage.delete(ALERT_KEY);
  persistentStorage.delete(REGION_KEY);
  persistentStorage.delete(TIME_KEY);

  if (!pendingAlert) return;
  if (Date.now() - pendingTime > MAX_AGE_MS) return;

  if (pendingAlert === 'threat') {
    ballisticAlertService.triggerThreat(pendingRegion || null);
  } else if (pendingAlert === 'all_clear') {
    ballisticAlertService.triggerAllClear(pendingRegion || null);
  }
}

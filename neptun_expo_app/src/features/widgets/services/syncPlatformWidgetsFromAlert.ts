import { Platform } from 'react-native';
import type { FcmData } from '../../notifications/services/fcmMessagePipeline';
import { liveActivityService } from './liveActivityService';
import { widgetService } from './widgetService';

function str(v: unknown): string {
  return v == null ? '' : String(v);
}

/**
 * Flutter `NotificationService._triggerAlertServices` widget + Live Activity side effects.
 */
export async function syncPlatformWidgetsFromAlert(data: FcmData): Promise<void> {
  const region = str(data.region);
  const threatType = str(data.threat_type);
  const alarmState = str(data.alarm_state);
  const body = str(data.body);
  const isAlarm = alarmState !== 'ended' && !body.toLowerCase().includes('відбій');

  if (Platform.OS === 'android') {
    await widgetService.updateAlarmStatus({
      isAlarm,
      region: region || null,
    });
  }

  if (Platform.OS === 'ios') {
    if (isAlarm && region) {
      await liveActivityService.start({
        region,
        threatType,
      });
    } else {
      await liveActivityService.end();
    }
  }
}

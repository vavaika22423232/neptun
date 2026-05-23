import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';
import { ttsService } from '../../../services/ttsService';
import { formatTtsMessage } from '../logic/formatTtsMessage';
import { notificationDedup } from '../notificationDedup';
import type { FcmData } from './fcmMessagePipeline';
import { syncPlatformWidgetsFromAlert } from '../../widgets/services/syncPlatformWidgetsFromAlert';
import { vibrateForAlert } from './alertHapticsService';

function str(v: unknown): string {
  return v == null ? '' : String(v);
}

/**
 * Flutter `_triggerAlertServices` after a notification is shown (foreground FCM).
 */
export async function triggerAlertFeedback(data: FcmData): Promise<void> {
  const region = str(data.region);
  const location = str(data.location ?? data.city);
  const threatType = str(data.threat_type);
  const alarmState = str(data.alarm_state);
  const body = str(data.body);
  const fcmType = str(data.type) || 'threat';

  if (fcmType === 'feedback_reply' || fcmType === 'feedback_status') {
    if (persistentStorage.getBoolean(PrefsKeys.vibrationEnabled, true)) {
      await vibrateForAlert(body);
    }
    return;
  }

  if (ttsService.isEnabled()) {
    const ttsKey = `${region}|${location}|${threatType}|${alarmState}`.toLowerCase();
    if (!notificationDedup.shouldSkipTts(ttsKey)) {
      const message = formatTtsMessage({ region, location, threatType, alarmState, body });
      await ttsService.speakDirect(message);
    }
  }

  await vibrateForAlert(body);
  await syncPlatformWidgetsFromAlert(data);
}

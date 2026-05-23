import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { PrefsKeys } from '../../../config/prefsKeys';
import { isPushNotificationsSupported } from '../../notifications/pushPlatform';
import { persistentStorage } from '../../../services/persistentStorage';
import {
  buildBriefingNotificationBody,
  buildBriefingNotificationTitle,
} from '../utils/briefingNotificationCopy';
import { briefingService } from './briefingService';

const BRIEFING_CHANNEL_ID = 'morning_briefing';
const BRIEFING_NOTIF_ID = '9901';

function todayKey(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function isMorningWindow(): boolean {
  const hour = new Date().getHours();
  return hour >= 8 && hour < 10;
}

async function ensureMorningBriefingChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync(BRIEFING_CHANNEL_ID, {
    name: 'Ранковий бріфінг',
    description: 'Щоденне зведення за ніч',
    importance: Notifications.AndroidImportance.HIGH,
  });
}

/**
 * Flutter `BriefingService.scheduleNotifications` — once per day between 8:00–10:00
 * when the app is foregrounded and notifications are enabled.
 */
export async function scheduleMorningBriefingIfNeeded(): Promise<void> {
  if (!isPushNotificationsSupported()) return;
  if (!isMorningWindow()) return;
  if (!persistentStorage.getBoolean(PrefsKeys.notificationsEnabled, true)) return;

  const lastSent = persistentStorage.getString(PrefsKeys.briefingLastSentDate) ?? '';
  const today = todayKey();
  if (lastSent === today) return;

  const { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') return;

  try {
    await ensureMorningBriefingChannel();
    const data = await briefingService.fetchBriefing();
    const title = buildBriefingNotificationTitle(data);
    const body = buildBriefingNotificationBody(data);

    await Notifications.scheduleNotificationAsync({
      identifier: BRIEFING_NOTIF_ID,
      content: {
        title,
        body,
        sound: true,
        data: { action: 'briefing', type: 'briefing' },
      },
      trigger: null,
    });

    persistentStorage.setString(PrefsKeys.briefingLastSentDate, today);
  } catch {
    /* non-fatal — briefing screen still loads data on demand */
  }
}

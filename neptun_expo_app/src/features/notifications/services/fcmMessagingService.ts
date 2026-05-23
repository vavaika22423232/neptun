import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { PrefsKeys } from '../../../config/prefsKeys';
import { expoHrefFromPushData } from '../../../core/navigation/pushDeepLink';
import { persistentStorage } from '../../../services/persistentStorage';
import { evaluateFcmMessage, type FcmData, type FcmDisplayPayload } from './fcmMessagePipeline';
import { triggerAlertFeedback } from './alertFeedbackService';
import { recordBallisticFromFcmIfNeeded } from './fcmBallisticPending';
import { fcmTopicService } from './fcmTopicService';

type RemoteMessage = {
  messageId?: string;
  data?: Record<string, string>;
  notification?: { title?: string; body?: string };
};

type NavigationHandler = (href: string) => void;

let navigateHandler: NavigationHandler | null = null;
let configured = false;
let foregroundUnsub: (() => void) | undefined;
let openedUnsub: (() => void) | undefined;

function normalizeData(raw: Record<string, unknown> | undefined): FcmData {
  if (!raw) return {};
  const out: FcmData = {};
  for (const [k, v] of Object.entries(raw)) {
    if (v != null) out[k] = String(v);
  }
  return out;
}

async function ensureAndroidChannels(channelId: string): Promise<void> {
  if (Platform.OS !== 'android') return;
  const vibration = persistentStorage.getBoolean(PrefsKeys.vibrationEnabled, true);
  const pattern = vibration ? [0, 250, 250, 250] : undefined;

  const channels: Record<
    string,
    { name: string; importance: Notifications.AndroidImportance }
  > = {
    feedback_alerts: {
      name: "Зворотний зв'язок",
      importance: Notifications.AndroidImportance.HIGH,
    },
    alarm_channel: {
      name: 'Тривоги',
      importance: Notifications.AndroidImportance.MAX,
    },
    critical_alerts: {
      name: 'Критичні тривоги',
      importance: Notifications.AndroidImportance.MAX,
    },
    normal_alerts: {
      name: 'Звичайні тривоги',
      importance: Notifications.AndroidImportance.HIGH,
    },
  };

  const spec = channels[channelId] ?? channels.normal_alerts;
  await Notifications.setNotificationChannelAsync(channelId, {
    name: spec.name,
    importance: spec.importance,
    vibrationPattern: pattern,
    lightColor: '#FF3B30',
  });
}

async function displayLocalNotification(payload: FcmDisplayPayload): Promise<void> {
  await ensureAndroidChannels(payload.channelId);
  await Notifications.scheduleNotificationAsync({
    content: {
      title: payload.title,
      body: payload.body,
      data: payload.data,
      sound: true,
      ...(Platform.OS === 'android' ? { channelId: payload.channelId } : {}),
    },
    trigger: null,
  });
}

async function handleRemoteMessage(
  message: RemoteMessage,
  foreground: boolean,
): Promise<void> {
  const data = normalizeData(message.data);
  if (!foreground) {
    recordBallisticFromFcmIfNeeded(data);
  }
  const result = evaluateFcmMessage(data, {
    foreground,
    notificationTitle: message.notification?.title,
    notificationBody: message.notification?.body,
  });
  if (!result.show) return;
  await displayLocalNotification(result.payload);
  await triggerAlertFeedback(data);
}

function navigateFromMessage(message: RemoteMessage): void {
  const data = message.data ?? {};
  const href = expoHrefFromPushData(data as Record<string, unknown>);
  navigateHandler?.(href);
}

export const fcmMessagingService = {
  setNavigationHandler(handler: NavigationHandler | null) {
    navigateHandler = handler;
  },

  configure(): void {
    if (configured || !fcmTopicService.isAvailable()) return;
    configured = true;

    const mod = fcmTopicService.getMessagingModule();
    if (!mod) return;

    const messaging = mod.default();

    foregroundUnsub?.();
    foregroundUnsub = messaging.onMessage(async (message: RemoteMessage) => {
      await handleRemoteMessage(message, true);
    });

    openedUnsub?.();
    openedUnsub = messaging.onMessageOpenedApp((message: RemoteMessage) => {
      navigateFromMessage(message);
    });
  },

  async handleInitialNotification(handler?: NavigationHandler | null): Promise<void> {
    if (!fcmTopicService.isAvailable()) return;
    const mod = fcmTopicService.getMessagingModule();
    if (!mod) return;
    const nav = handler ?? navigateHandler;
    if (!nav) return;
    const message = await mod.default().getInitialMessage();
    if (message) {
      const data = message.data ?? {};
      const href = expoHrefFromPushData(data as Record<string, unknown>);
      setTimeout(() => nav(href), 600);
    }
  },

  /** Top-level background handler — data-only FCM while app is backgrounded/killed. */
  async handleBackgroundMessage(message: RemoteMessage): Promise<void> {
    await handleRemoteMessage(message, false);
  },

  teardown(): void {
    foregroundUnsub?.();
    foregroundUnsub = undefined;
    openedUnsub?.();
    openedUnsub = undefined;
    configured = false;
  },
};

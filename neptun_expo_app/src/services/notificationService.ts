import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { isPushNotificationsSupported } from '../features/notifications/pushPlatform';

export { isPushNotificationsSupported };
import { endpoints } from '../config/api';
import { PrefsKeys } from '../config/prefsKeys';
import { expoHrefFromPushData } from '../core/navigation/pushDeepLink';
import { buildFcmTopics, persistRegionIdsFromSelection } from '../features/notifications/utils/buildFcmTopics';
import { fcmMessagingService } from '../features/notifications/services/fcmMessagingService';
import { fcmTopicService } from '../features/notifications/services/fcmTopicService';
import { appLogger } from '../core/logging/appLogger';
import { apiRequest } from './apiClient';
import { authService } from './authService';
import { persistentStorage } from './persistentStorage';
import { notificationDedup } from '../features/notifications/notificationDedup';
import { notificationPrefsController } from '../features/notifications/notificationPrefsController';
import { briefingService } from '../features/briefing/services/briefingService';
import { widgetService } from '../features/widgets/services/widgetService';
import { scheduleMorningBriefingIfNeeded } from '../features/briefing/services/briefingMorningNotification';
import { shouldBlockSleepNotification } from './sleepModeStore';
import { storage } from './storage';

type NavigationHandler = (href: string) => void;

let navigateHandler: NavigationHandler | null = null;

async function authedRegister(body: Record<string, unknown>): Promise<void> {
  let token = await authService.getAccessToken();
  if (!token) {
    await authService.login();
    token = await authService.getAccessToken();
  }
  await apiRequest(endpoints.registerDevice, {
    method: 'POST',
    authToken: token,
    body: JSON.stringify(body),
  });
}

async function resolvePushToken(): Promise<string | null> {
  if (fcmTopicService.isAvailable()) {
    const fcm = await fcmTopicService.getFcmToken();
    if (fcm) {
      persistentStorage.setString(PrefsKeys.fcmToken, fcm);
      return fcm;
    }
  }
  if (!isPushNotificationsSupported() || !Device.isDevice) return null;
  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    persistentStorage.setString(PrefsKeys.fcmToken, tokenData.data);
    return tokenData.data;
  } catch {
    return null;
  }
}

export const notificationService = {
  configureForegroundHandler() {
    if (!isPushNotificationsSupported()) return;
    fcmMessagingService.configure();
    Notifications.setNotificationHandler({
      handleNotification: async (notification) => {
        const title = notification.request.content.title ?? '';
        const body = notification.request.content.body ?? '';
        const dedupKey = `${title}|${body}`;
        if (notificationDedup.shouldSkipNotification(dedupKey)) {
          return {
            shouldShowBanner: false,
            shouldShowList: false,
            shouldPlaySound: false,
            shouldSetBadge: false,
          };
        }
        const blocked = shouldBlockSleepNotification(`${title}\n${body}`);
        return {
          shouldShowBanner: !blocked,
          shouldShowList: !blocked,
          shouldPlaySound: !blocked,
          shouldSetBadge: true,
        };
      },
    });
  },

  setNavigationHandler(handler: NavigationHandler | null) {
    navigateHandler = handler;
  },

  async registerForPushNotifications(): Promise<string | null> {
    if (!isPushNotificationsSupported() || !Device.isDevice) return null;

    const { status: existing } = await Notifications.getPermissionsAsync();
    let finalStatus = existing;
    if (existing !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') {
      appLogger.error('permission', `Push permission: ${finalStatus}`);
      return null;
    }

    await fcmTopicService.ensureIosRemoteMessages();
    void fcmTopicService.requestFcmPermission();

    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('alarm_channel', {
        name: 'Тривоги',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#FF3B30',
      });
      await Notifications.setNotificationChannelAsync('normal_alerts', {
        name: 'Звичайні тривоги',
        importance: Notifications.AndroidImportance.HIGH,
      });
    }

    const token = await resolvePushToken();
    if (!token) return null;

    const deviceId = await storage.getDeviceId();
    try {
      await authedRegister({
        device_id: deviceId,
        token,
        platform: Platform.OS,
      });
      await notificationPrefsController.syncToBackend(deviceId, token);
    } catch (e) {
      appLogger.error('notification', 'Device register failed', e);
    }

    if (persistentStorage.getBoolean(PrefsKeys.notificationsEnabled, true)) {
      const regions = persistentStorage.getStringList(PrefsKeys.selectedRegions);
      if (regions.length > 0) {
        await this.updateRegions(regions);
      } else {
        const savedTopics = persistentStorage.getStringList(PrefsKeys.subscribedTopics);
        if (savedTopics.length > 0 && fcmTopicService.isAvailable()) {
          await fcmTopicService.subscribeTopics(savedTopics);
        }
      }
    }

    fcmTopicService.setupTokenRefresh((newToken) => {
      persistentStorage.setString(PrefsKeys.fcmToken, newToken);
      void storage.getDeviceId().then((deviceId) => {
        void authedRegister({
          device_id: deviceId,
          token: newToken,
          platform: Platform.OS,
        }).catch(() => undefined);
      });
    });

    return token;
  },

  /**
   * Flutter `NotificationService.updateRegions` — FCM topics + backend prefs.
   */
  async updateRegions(selectedRegions: string[]): Promise<void> {
    if (selectedRegions.length === 0) {
      const saved = persistentStorage.getStringList(PrefsKeys.selectedRegions);
      if (saved.length > 0) {
        await this.updateRegions(saved);
        return;
      }
    }

    const { oblastIds, raionIds } = persistRegionIdsFromSelection(selectedRegions);
    persistentStorage.setStringList(PrefsKeys.selectedRegions, selectedRegions);
    persistentStorage.setStringList('selected_oblast_ids', oblastIds);
    persistentStorage.setStringList('selected_raion_ids', raionIds);

    const topics = buildFcmTopics(selectedRegions);
    persistentStorage.setStringList(PrefsKeys.subscribedTopics, topics);
    persistentStorage.setStringList(PrefsKeys.subscribedRegions, topics);
    briefingService.invalidateCache();
    const primaryRegion = selectedRegions[0]?.trim();
    if (primaryRegion) {
      void widgetService.setUserRegion(primaryRegion);
    }

    if (fcmTopicService.isAvailable()) {
      await fcmTopicService.unsubscribeFromAllKnownTopics();
      await fcmTopicService.subscribeTopics(topics);
    }

    const deviceId = await storage.getDeviceId();
    const token = persistentStorage.getString(PrefsKeys.fcmToken) ?? (await resolvePushToken());
    try {
      if (selectedRegions.length === 0) {
        await authedRegister({
          device_id: deviceId,
          token: token ?? '',
          platform: Platform.OS,
          enabled: false,
        });
      } else {
        if (token) {
          await authedRegister({
            device_id: deviceId,
            token,
            platform: Platform.OS,
            regions: selectedRegions,
            oblast_ids: oblastIds,
            raion_ids: raionIds,
          });
        }
        await notificationPrefsController.syncToBackend(deviceId, token);
      }
    } catch {
      /* graceful when API unavailable */
    }
  },

  handleNotificationResponse(response: Notifications.NotificationResponse) {
    const data = (response.notification.request.content.data ?? {}) as Record<string, unknown>;
    const href = expoHrefFromPushData(data);
    navigateHandler?.(href);
  },

  handleInitialNotification(handler?: NavigationHandler | null) {
    if (!isPushNotificationsSupported()) return;
    const nav = handler ?? navigateHandler;
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (!response || !nav) return;
      const data = (response.notification.request.content.data ?? {}) as Record<string, unknown>;
      nav(expoHrefFromPushData(data));
    });
  },

  subscribe() {
    if (!isPushNotificationsSupported()) return () => undefined;
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      this.handleNotificationResponse(response);
    });
    return () => sub.remove();
  },

  async syncPreferencesToBackend(): Promise<void> {
    const deviceId = await storage.getDeviceId();
    const token = persistentStorage.getString(PrefsKeys.fcmToken) ?? null;
    await notificationPrefsController.syncToBackend(deviceId, token);
  },

  /** Flutter `NotificationService.setNotificationsEnabled` */
  async setNotificationsEnabled(enabled: boolean): Promise<void> {
    persistentStorage.setBoolean(PrefsKeys.notificationsEnabled, enabled);
    if (!enabled) {
      persistentStorage.setBoolean(PrefsKeys.ttsEnabled, false);
      if (fcmTopicService.isAvailable()) {
        await fcmTopicService.unsubscribeFromAllKnownTopics();
      }
      persistentStorage.setStringList(PrefsKeys.subscribedTopics, []);
    } else {
      let saved = persistentStorage.getStringList(PrefsKeys.selectedRegions);
      if (saved.length === 0) {
        const oblastIds = persistentStorage.getStringList('selected_oblast_ids');
        if (oblastIds.length > 0) {
          /* names restored on next regions screen save */
        }
      }
      if (saved.length > 0) {
        await this.updateRegions(saved);
      } else {
        const topics = persistentStorage.getStringList(PrefsKeys.subscribedTopics);
        if (topics.length > 0 && fcmTopicService.isAvailable()) {
          await fcmTopicService.subscribeTopics(topics);
        }
      }
    }
    await this.syncPreferencesToBackend();
  },

  /** Flutter `BriefingService.scheduleNotifications` on foreground / after init. */
  scheduleMorningBriefingIfNeeded(): void {
    void scheduleMorningBriefingIfNeeded();
  },

  async sendTestNotification(): Promise<void> {
    if (!isPushNotificationsSupported()) {
      throw new Error('Сповіщення недоступні на цій платформі');
    }

    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'NEPTUN — тест',
        body: 'Локальне тестове сповіщення',
        sound: true,
      },
      trigger: null,
    });

    const token = persistentStorage.getString(PrefsKeys.fcmToken);
    if (!token) return;

    try {
      await apiRequest(endpoints.testNotification, {
        method: 'POST',
        body: JSON.stringify({ token }),
      });
    } catch {
      /* backend optional */
    }
  },
};

import { Platform } from 'react-native';
import { isFirebaseNativeLinked } from '../../../utils/nativeModuleGuard';
import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';
import { allKnownRegionTopics } from '../utils/regionToTopic';

type RemoteMessage = {
  messageId?: string;
  data?: Record<string, string>;
  notification?: { title?: string; body?: string };
};

export type MessagingModule = {
  default: () => {
    subscribeToTopic: (topic: string) => Promise<void>;
    unsubscribeFromTopic: (topic: string) => Promise<void>;
    getToken: () => Promise<string>;
    getAPNSToken: () => Promise<string | null>;
    requestPermission: () => Promise<number>;
    registerDeviceForRemoteMessages: () => Promise<void>;
    onTokenRefresh: (cb: (token: string) => void) => () => void;
    onMessage: (cb: (msg: RemoteMessage) => void | Promise<void>) => () => void;
    onMessageOpenedApp: (cb: (msg: RemoteMessage) => void) => () => void;
    getInitialMessage: () => Promise<RemoteMessage | null>;
    setBackgroundMessageHandler: (handler: (msg: RemoteMessage) => Promise<void>) => void;
  };
};

let messagingMod: MessagingModule | null | undefined;
let apnsReady = Platform.OS !== 'ios';
let pendingResubscribe = false;
let retryTimer: ReturnType<typeof setInterval> | null = null;

function getMessaging() {
  if (messagingMod !== undefined) return messagingMod;
  if (!isFirebaseNativeLinked()) {
    messagingMod = null;
    return messagingMod;
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    messagingMod = require('@react-native-firebase/messaging') as MessagingModule;
  } catch {
    messagingMod = null;
  }
  return messagingMod;
}

export const fcmTopicService = {
  isAvailable(): boolean {
    return getMessaging() != null;
  },

  getMessagingModule(): MessagingModule | null {
    return getMessaging() ?? null;
  },

  async ensureIosRemoteMessages(): Promise<void> {
    const mod = getMessaging();
    if (!mod || Platform.OS !== 'ios') return;
    try {
      await mod.default().registerDeviceForRemoteMessages();
    } catch {
      /* already registered */
    }
  },

  async requestFcmPermission(): Promise<boolean> {
    const mod = getMessaging();
    if (!mod) return false;
    try {
      const status = await mod.default().requestPermission();
      return status === 1 || status === 2;
    } catch {
      return false;
    }
  },

  async getFcmToken(): Promise<string | null> {
    const mod = getMessaging();
    if (!mod) return null;
    try {
      if (Platform.OS === 'ios') {
        const apns = await mod.default().getAPNSToken();
        if (!apns) return null;
        apnsReady = true;
      }
      return await mod.default().getToken();
    } catch {
      return null;
    }
  },

  async safeSubscribe(topic: string): Promise<boolean> {
    const mod = getMessaging();
    if (!mod) return false;
    if (Platform.OS === 'ios' && !apnsReady) return false;
    try {
      await mod.default().subscribeToTopic(topic);
      return true;
    } catch {
      return false;
    }
  },

  async safeUnsubscribe(topic: string): Promise<void> {
    const mod = getMessaging();
    if (!mod) return;
    if (Platform.OS === 'ios' && !apnsReady) return;
    try {
      await mod.default().unsubscribeFromTopic(topic);
    } catch {
      /* ignore */
    }
  },

  async unsubscribeFromAllKnownTopics(): Promise<void> {
    for (const topic of allKnownRegionTopics()) {
      await this.safeUnsubscribe(topic);
    }
  },

  async subscribeTopics(topics: string[]): Promise<{ success: number; total: number }> {
    let success = 0;
    for (const topic of topics) {
      if (await this.safeSubscribe(topic)) success += 1;
    }
    if (Platform.OS === 'ios' && success === 0 && topics.length > 0) {
      pendingResubscribe = true;
      this.scheduleApnsRetry();
    } else {
      pendingResubscribe = false;
    }
    return { success, total: topics.length };
  },

  scheduleApnsRetry(): void {
    if (retryTimer) return;
    let attempts = 0;
    retryTimer = setInterval(() => {
      attempts += 1;
      void (async () => {
        const mod = getMessaging();
        if (!mod) {
          this.clearRetry();
          return;
        }
        try {
          const apns = await mod.default().getAPNSToken();
          if (apns) {
            apnsReady = true;
            await this.resubscribeFromSavedTopics();
            this.clearRetry();
          } else if (attempts >= 12) {
            this.clearRetry();
          }
        } catch {
          if (attempts >= 12) this.clearRetry();
        }
      })();
    }, 5000);
  },

  clearRetry(): void {
    if (retryTimer) {
      clearInterval(retryTimer);
      retryTimer = null;
    }
  },

  async resubscribeFromSavedTopics(): Promise<void> {
    if (!pendingResubscribe) return;
    const saved = persistentStorage.getStringList(PrefsKeys.subscribedTopics);
    if (saved.length === 0) {
      pendingResubscribe = false;
      return;
    }
    await this.subscribeTopics(saved);
    pendingResubscribe = false;
  },

  setupTokenRefresh(onToken: (token: string) => void): (() => void) | undefined {
    const mod = getMessaging();
    if (!mod) return undefined;
    return mod.default().onTokenRefresh(onToken);
  },

  configureBackgroundHandler(handler: (msg: RemoteMessage) => Promise<void>): void {
    const mod = getMessaging();
    if (!mod) return;
    mod.default().setBackgroundMessageHandler(handler);
  },
};

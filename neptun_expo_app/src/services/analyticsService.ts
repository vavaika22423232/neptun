import { Platform } from 'react-native';
import { isFirebaseNativeLinked } from '../utils/nativeModuleGuard';

type FirebaseAnalytics = {
  (): {
    setAnalyticsCollectionEnabled: (enabled: boolean) => Promise<void>;
    logEvent: (name: string, params?: Record<string, unknown>) => Promise<void>;
    logScreenView: (params: { screen_name: string; screen_class?: string }) => Promise<void>;
  };
};

let analyticsFactory: FirebaseAnalytics | null | undefined;
let analyticsFailed = false;
let collectionEnabled = false;

function getAnalytics() {
  if (analyticsFailed || Platform.OS === 'web') return null;
  if (!isFirebaseNativeLinked()) {
    analyticsFactory = null;
    return null;
  }
  if (analyticsFactory !== undefined) return analyticsFactory;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    analyticsFactory = require('@react-native-firebase/analytics').default as FirebaseAnalytics;
  } catch {
    analyticsFailed = true;
    analyticsFactory = null;
  }
  return analyticsFactory;
}

function sanitizeParams(params?: Record<string, unknown>): Record<string, string | number> {
  if (!params) return {};
  const out: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v == null) continue;
    if (typeof v === 'string' || typeof v === 'number') out[k] = v;
    else out[k] = String(v);
  }
  return out;
}

/** Flutter `FirebaseAnalytics` — lazy, no crash without native rebuild. */
export const analyticsService = {
  isAvailable(): boolean {
    return getAnalytics() != null;
  },

  async initialize(): Promise<void> {
    const factory = getAnalytics();
    if (!factory || collectionEnabled) return;
    try {
      await factory().setAnalyticsCollectionEnabled(true);
      collectionEnabled = true;
    } catch {
      analyticsFailed = true;
    }
  },

  async logEvent(name: string, params?: Record<string, unknown>): Promise<void> {
    const factory = getAnalytics();
    if (!factory) return;
    try {
      await factory().logEvent(name, sanitizeParams(params));
    } catch {
      /* optional */
    }
  },

  async logScreenView(screenName: string): Promise<void> {
    const factory = getAnalytics();
    if (!factory || !screenName) return;
    try {
      await factory().logScreenView({
        screen_name: screenName,
        screen_class: screenName,
      });
    } catch {
      /* optional */
    }
  },
};

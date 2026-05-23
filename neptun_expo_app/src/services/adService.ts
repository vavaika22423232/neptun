import { AppState, type AppStateStatus, Platform } from 'react-native';
import { appOpenAdUnitId } from '../config/adUnits';
import { PrefsKeys } from '../config/prefsKeys';
import { getGoogleMobileAds, isGoogleMobileAdsAvailable } from '../utils/lazyGoogleMobileAds';
import { persistentStorage } from './persistentStorage';

const LAST_APP_OPEN_KEY = 'last_app_open_ad_shown';
const APP_OPEN_COOLDOWN_MS = 90 * 60 * 1000;
const MIN_BACKGROUND_MS = __DEV__ ? 3_000 : 15_000;
const MAX_BANNER_REQUESTS = 5;
const BANNER_THROTTLE_MS = 120_000;

let initialized = false;
let isPremium = false;
let sessionActive = false;
let bannerLoaded = false;
let bannerRequestCount = 0;
let lastBannerRequestAt = 0;
let hasShownColdStartAppOpen = false;
let backgroundedAt: number | null = null;

let appOpenAd: {
  load: () => void;
  show: () => void;
  addAdEventListener: (event: string, listener: () => void) => () => void;
} | null = null;
let appOpenLoaded = false;

const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((fn) => fn());
}

function isAdFree(): boolean {
  const until = Number(persistentStorage.getString(PrefsKeys.adFreeUntil) ?? '0');
  return until > Date.now();
}

function hydratePremium(): void {
  isPremium = persistentStorage.getBoolean(PrefsKeys.isPremium, false);
}

function canShowAppOpen(): boolean {
  const last = Number(persistentStorage.getString(LAST_APP_OPEN_KEY) ?? '0');
  if (!last) return true;
  return Date.now() - last >= APP_OPEN_COOLDOWN_MS;
}

function recordAppOpenShown(): void {
  persistentStorage.setString(LAST_APP_OPEN_KEY, String(Date.now()));
}

function shouldLoadAds(): boolean {
  return isGoogleMobileAdsAvailable() && !isPremium && !isAdFree();
}

const REWARDED_AD_FREE_MS = 4 * 60 * 60 * 1000;
const REWARDED_HISTORY_UNLOCK_MS = 24 * 60 * 60 * 1000;

export const adService = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  isNativeAvailable(): boolean {
    return isGoogleMobileAdsAvailable();
  },

  isBannerVisible(): boolean {
    return shouldLoadAds() && bannerLoaded && initialized;
  },

  canRequestBanner(): boolean {
    if (!shouldLoadAds() || !initialized) return false;
    if (__DEV__) return true;
    if (bannerRequestCount >= MAX_BANNER_REQUESTS) return false;
    if (Date.now() - lastBannerRequestAt < BANNER_THROTTLE_MS) return false;
    return true;
  },

  markBannerRequest(): void {
    bannerRequestCount += 1;
    lastBannerRequestAt = Date.now();
  },

  setBannerLoaded(loaded: boolean): void {
    bannerLoaded = loaded;
    notify();
  },

  markSessionActive(): void {
    sessionActive = true;
  },

  setPremiumStatus(premium: boolean): void {
    isPremium = premium;
    if (premium) {
      bannerLoaded = false;
      appOpenAd = null;
      appOpenLoaded = false;
    }
    notify();
  },

  /** Sync from server entitlements (adsDisabled includes lifetime PRO). */
  syncAdsFromEntitlements(adsDisabled: boolean): void {
    const wasBlocked = isPremium || isAdFree();
    isPremium = adsDisabled;
    if (adsDisabled) {
      bannerLoaded = false;
      appOpenAd = null;
      appOpenLoaded = false;
    } else if (wasBlocked && shouldLoadAds()) {
      if (!initialized) {
        void adService.initialize();
      } else {
        loadAppOpenAd();
      }
    }
    notify();
  },

  /** Dev / support: why ads may be hidden */
  getDiagnostics(): {
    nativeLinked: boolean;
    initialized: boolean;
    isPremiumFlag: boolean;
    adFreeUntil: number;
    adFreeActive: boolean;
    canLoadAds: boolean;
    bannerLoaded: boolean;
    sessionActive: boolean;
    platform: string;
  } {
    hydratePremium();
    return {
      nativeLinked: isGoogleMobileAdsAvailable(),
      initialized,
      isPremiumFlag: isPremium,
      adFreeUntil: Number(persistentStorage.getString(PrefsKeys.adFreeUntil) ?? '0'),
      adFreeActive: isAdFree(),
      canLoadAds: shouldLoadAds(),
      bannerLoaded,
      sessionActive,
      platform: Platform.OS,
    };
  },

  startRewardedAdFreeHours(hours = 4): void {
    const until = Date.now() + hours * 60 * 60 * 1000;
    persistentStorage.setString(PrefsKeys.adFreeUntil, String(until));
    bannerLoaded = false;
    notify();
  },

  startRewardedHistoryUnlockHours(hours = 24): void {
    const until = Date.now() + hours * 60 * 60 * 1000;
    persistentStorage.setString(PrefsKeys.historyUnlockUntil, String(until));
  },

  isHistoryUnlockedByReward(): boolean {
    const until = Number(persistentStorage.getString(PrefsKeys.historyUnlockUntil) ?? '0');
    return until > Date.now();
  },

  getRewardedAdFreeDurationMs(): number {
    return REWARDED_AD_FREE_MS;
  },

  getRewardedHistoryUnlockMs(): number {
    return REWARDED_HISTORY_UNLOCK_MS;
  },

  setAdFreeUntil(untilMs: number): void {
    persistentStorage.setString(PrefsKeys.adFreeUntil, String(untilMs));
    if (isAdFree()) {
      bannerLoaded = false;
      notify();
    }
  },

  async initialize(): Promise<void> {
    if (initialized || Platform.OS === 'web') return;

    const mod = getGoogleMobileAds();
    if (!mod) return;

    hydratePremium();
    const adFreeMillis = persistentStorage.getString(PrefsKeys.adFreeUntil);
    if (adFreeMillis) {
      const n = Number(adFreeMillis);
      if (n <= Date.now()) persistentStorage.delete(PrefsKeys.adFreeUntil);
    }

    if (isPremium) return;

    try {
      await mod.default().initialize();
      try {
        await mod.default().setRequestConfiguration({
          maxAdContentRating: mod.MaxAdContentRating.G,
        });
      } catch {
        /* optional */
      }
      initialized = true;
      notify();

      if (shouldLoadAds()) {
        loadAppOpenAd();
        const coldDelay = __DEV__ ? 4000 : 5000;
        setTimeout(() => void tryColdStartAppOpen(), coldDelay);
      }
    } catch {
      initialized = false;
    }
  },

  onAppStateChange(next: AppStateStatus): void {
    if (next === 'background' || next === 'inactive') {
      backgroundedAt = Date.now();
      return;
    }
    if (next === 'active') {
      void onAppResumed();
    }
  },
};

function loadAppOpenAd(): void {
  const mod = getGoogleMobileAds();
  if (!mod || !shouldLoadAds() || appOpenLoaded) return;

  const unitId = appOpenAdUnitId();
  if (!unitId) return;

  const ad = mod.AppOpenAd.createForAdRequest(unitId) as NonNullable<typeof appOpenAd>;
  appOpenAd = ad;
  ad.addAdEventListener(mod.AdEventType.LOADED, () => {
    appOpenLoaded = true;
  });
  ad.addAdEventListener(mod.AdEventType.ERROR, () => {
    appOpenLoaded = false;
    appOpenAd = null;
  });
  ad.addAdEventListener(mod.AdEventType.OPENED, () => {
    recordAppOpenShown();
    backgroundedAt = null;
  });
  ad.addAdEventListener(mod.AdEventType.CLOSED, () => {
    appOpenLoaded = false;
    appOpenAd = null;
    backgroundedAt = null;
    loadAppOpenAd();
  });
  ad.load();
}

function showAppOpenAd(): void {
  const mod = getGoogleMobileAds();
  if (!mod || !appOpenAd || !appOpenLoaded) {
    loadAppOpenAd();
    return;
  }
  try {
    appOpenAd.show();
  } catch {
    appOpenAd = null;
    appOpenLoaded = false;
  }
}

async function tryColdStartAppOpen(): Promise<void> {
  if (hasShownColdStartAppOpen || !sessionActive || isPremium || isAdFree()) return;
  if (!__DEV__ && !canShowAppOpen()) return;

  if (!appOpenLoaded) {
    loadAppOpenAd();
    await new Promise((r) => setTimeout(r, 3000));
  }
  if (appOpenLoaded) {
    hasShownColdStartAppOpen = true;
    showAppOpenAd();
  }
}

async function onAppResumed(): Promise<void> {
  hydratePremium();
  if (isPremium || isAdFree()) return;

  if (__DEV__) {
    if (backgroundedAt != null && Date.now() - backgroundedAt >= MIN_BACKGROUND_MS) {
      showAppOpenAd();
    }
    return;
  }

  if (!sessionActive) return;
  if (backgroundedAt == null) return;
  if (Date.now() - backgroundedAt < MIN_BACKGROUND_MS) return;
  if (!canShowAppOpen()) {
    loadAppOpenAd();
    return;
  }

  showAppOpenAd();
}

/** Register AppState listener once from shell bootstrap. */
export function bindAdAppStateListener(): () => void {
  const sub = AppState.addEventListener('change', adService.onAppStateChange);
  return () => sub.remove();
}

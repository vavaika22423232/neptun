import { Platform } from 'react-native';
import type { Purchase } from 'expo-iap';
import { endpoints } from '../config/api';
import { appLogger } from '../core/logging/appLogger';
import { PrefsKeys } from '../config/prefsKeys';
import {
  IAP_ALL_KNOWN_IDS,
  IAP_LEGACY_PRO_IDS,
  IAP_LIFETIME_LEGACY,
  IAP_MAX_MONTHLY,
  IAP_PRO_MONTHLY,
  IAP_PRO_PLUS_MONTHLY,
} from '../features/monetization/constants/iapProducts';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { entitlementsService } from './entitlementsService';
import {
  extractPurchaseCredentials,
  finishNativePurchase,
  getLoadedStoreProducts,
  initNativeIap,
  isAlreadyOwnedMessage,
  isNativeIapSupported,
  loadNativeProducts,
  requestNativePurchase,
  restoreNativePurchases,
  type StoreProduct,
} from '../features/premium/services/nativeIap';
import { apiGet, apiRequest } from './apiClient';
import { authService } from './authService';
import { adService } from './adService';
import { persistentStorage } from './persistentStorage';
import { storage } from './storage';

export type AppTier = 'free' | 'pro' | 'pro_plus' | 'max';

function tierFromProductId(productId: string): AppTier {
  if (productId === IAP_MAX_MONTHLY) return 'max';
  if (productId === IAP_PRO_PLUS_MONTHLY) return 'pro_plus';
  if (productId === IAP_PRO_MONTHLY || productId === 'pro_monthly') return 'pro';
  if (
    productId === IAP_LIFETIME_LEGACY ||
    IAP_LEGACY_PRO_IDS.includes(productId as (typeof IAP_LEGACY_PRO_IDS)[number])
  ) {
    return 'pro_plus';
  }
  return 'pro';
}

const IAP_SECURE = {
  productId: 'iap_premium_product_id',
  token: 'iap_premium_token',
  source: 'iap_premium_source',
} as const;

const PRO_PRODUCT_IDS = new Set<string>(IAP_ALL_KNOWN_IDS);

let isPremium = false;
let tier: AppTier = 'free';
let debugOverride = false;
let initialized = false;
let storeProducts: StoreProduct[] = [];
let lastVerificationMs = 0;
const VERIFICATION_COOLDOWN_MS = 60 * 60 * 1000;

const listeners = new Set<() => void>();
let onPurchaseSuccess: (() => void) | null = null;
let onPurchaseError: ((msg: string) => void) | null = null;

function notify(): void {
  listeners.forEach((fn) => fn());
}

function tierFromString(value: string | null | undefined): AppTier {
  if (value === 'max' || value === 'pro_plus' || value === 'pro') return value;
  return 'free';
}

async function loadLocalPremiumStatus(): Promise<void> {
  isPremium = persistentStorage.getBoolean(PrefsKeys.isPremium, false);
  tier = tierFromString(persistentStorage.getString(PrefsKeys.activeTier));
  if (isPremium && tier === 'free') {
    tier = 'pro';
    persistentStorage.setString(PrefsKeys.activeTier, 'pro');
  }
}

async function savePremiumStatus(value: boolean, nextTier: AppTier = 'pro'): Promise<void> {
  isPremium = value;
  tier = value ? nextTier : 'free';
  persistentStorage.setBoolean(PrefsKeys.isPremium, value);
  persistentStorage.setString(PrefsKeys.activeTier, tier);
  await storage.setPremium(value);
  adService.setPremiumStatus(value);
  void import('../features/widgets/services/widgetService').then(({ widgetService }) => {
    if (value) {
      void widgetService.getUserRegion().then((region) =>
        widgetService.updateWidget({
          region: region ?? 'Всі регіони',
          isAlarm: false,
          threatsCount: 0,
          timerMinutes: 0,
        }),
      );
    } else {
      void widgetService.applyNonPremiumWidgetState();
    }
  });
  notify();
}

async function revokePremiumLocal(): Promise<void> {
  await savePremiumStatus(false, 'free');
  await storage.secureDelete(IAP_SECURE.productId);
  await storage.secureDelete(IAP_SECURE.token);
  await storage.secureDelete(IAP_SECURE.source);
}

async function readIapCredential(key: string): Promise<string | null> {
  return storage.secureGet(key);
}

async function ensureAuthToken(): Promise<string | null> {
  let token = await authService.getAccessToken();
  if (!token) {
    await authService.login();
    token = await authService.getAccessToken();
  }
  return token;
}

async function postEntitlementRegister(
  deviceId: string,
  productId: string,
  purchaseToken: string,
  source: string,
): Promise<'success' | 'denied' | 'transient' | 'noCredentials'> {
  const token = purchaseToken.trim();
  const pid = productId.trim();
  if (!token || !pid) return 'noCredentials';
  const verifyPath =
    source === 'app_store' || Platform.OS === 'ios'
      ? endpoints.v1PurchasesAppleVerify
      : endpoints.v1PurchasesGoogleVerify;
  try {
    const data = await apiRequest<{ ok?: boolean; reason?: string }>(verifyPath, {
      method: 'POST',
      authToken: await ensureAuthToken(),
      body: JSON.stringify({
        deviceId,
        productId: pid,
        purchaseToken: token,
        source: source === 'app_store' ? 'app_store' : 'google_play',
        platform: Platform.OS,
      }),
      timeoutMs: 22_000,
    });
    if (data.ok) return 'success';
    if (data.reason === 'pending' || data.reason === 'transient') return 'transient';
    return 'denied';
  } catch {
    return 'transient';
  }
}

async function tryBindEntitlementFromStored(deviceId: string): Promise<'success' | 'denied' | 'transient' | 'none'> {
  const productId = await readIapCredential(IAP_SECURE.productId);
  const purchaseToken = await readIapCredential(IAP_SECURE.token);
  const source = (await readIapCredential(IAP_SECURE.source)) ?? 'unknown';
  if (!productId || !purchaseToken) return 'none';
  const result = await postEntitlementRegister(deviceId, productId, purchaseToken, source);
  if (result === 'success') {
    await savePremiumStatus(true, tierFromProductId(productId));
    return 'success';
  }
  if (result === 'denied') return 'denied';
  if (result === 'transient') return 'transient';
  return 'none';
}

async function syncEntitlementWithServerInner(): Promise<void> {
  const deviceId = await authService.getDeviceId();
  if (!deviceId) return;

  try {
    const ent = await entitlementsService.syncFromServer();
    if (ent.isPro) {
      if (!isPremium) await savePremiumStatus(true, ent.plan === 'free' ? 'pro' : (ent.plan as AppTier));
      return;
    }

    const gd = await apiGet<Record<string, unknown>>(
      `${endpoints.premiumEntitlement}?deviceId=${encodeURIComponent(deviceId)}`,
      { authToken: await ensureAuthToken(), timeoutMs: 15_000 },
    );
    if (gd.entitled === true) {
      if (!isPremium) await savePremiumStatus(true, 'pro');
      return;
    }
    if (gd.revoked === true) {
      await revokePremiumLocal();
      return;
    }
    if (gd.noBinding === true && isPremium) {
      const bind = await tryBindEntitlementFromStored(deviceId);
      if (bind === 'success' || bind === 'transient') return;
      const hasCreds = !!(await readIapCredential(IAP_SECURE.token));
      if (hasCreds && bind === 'denied') {
        await revokePremiumLocal();
      }
    }
  } catch (e) {
    appLogger.error('purchase', 'Entitlement sync failed', e);
  }
}

async function applyDebugPremiumIfNeeded(): Promise<void> {
  if (!__DEV__) {
    persistentStorage.delete(PrefsKeys.debugPremium);
    if (debugOverride) {
      debugOverride = false;
      notify();
    }
    return;
  }
  const fromEnv = process.env.EXPO_PUBLIC_DEBUG_PRO === 'true';
  if (!fromEnv) {
    persistentStorage.delete(PrefsKeys.debugPremium);
    debugOverride = false;
    notify();
    return;
  }
  debugOverride = true;
  persistentStorage.setBoolean(PrefsKeys.debugPremium, true);
  notify();
}

async function verifyPurchaseOnServer(
  productId: string,
  purchaseToken: string,
  source: string,
): Promise<boolean> {
  const deviceId = await authService.getDeviceId();
  if (!deviceId) return false;

  let authToken = await authService.getAccessToken();
  if (!authToken) {
    await authService.login();
    authToken = await authService.getAccessToken();
  }

  const verifyPath =
    source === 'app_store' || Platform.OS === 'ios'
      ? endpoints.v1PurchasesAppleVerify
      : endpoints.v1PurchasesGoogleVerify;

  const maxRetries = 5;
  let sawTransient = false;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const data = await apiRequest<{ ok?: boolean; reason?: string }>(verifyPath, {
        method: 'POST',
        authToken,
        body: JSON.stringify({
          deviceId,
          productId,
          purchaseToken,
          source: source === 'app_store' ? 'app_store' : 'google_play',
          platform: Platform.OS,
        }),
        timeoutMs: 22_000,
      });
      if (data.ok === true || (data as { valid?: boolean }).valid === true) return true;
      if (data.reason === 'pending' || data.reason === 'transient') {
        sawTransient = true;
        if (attempt < maxRetries) await delay(500 * attempt);
        continue;
      }
      return false;
    } catch {
      sawTransient = true;
      if (attempt < maxRetries) await delay(500 * attempt);
    }
  }

  if (sawTransient) {
    appLogger.error('purchase', 'Purchase verification incomplete after retries');
  }
  return false;
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function deliverPurchase(purchase: Purchase, skipVerify: boolean): Promise<void> {
  const { productId, token, source } = extractPurchaseCredentials(purchase);
  if (!PRO_PRODUCT_IDS.has(productId)) return;

  if (!skipVerify && token) {
    const valid = await verifyPurchaseOnServer(productId, token, source);
    if (!valid) {
      onPurchaseError?.call(null, 'Не вдалося підтвердити покупку');
      return;
    }
  } else if (!skipVerify && !token) {
    onPurchaseError?.call(null, 'Не вдалося підтвердити покупку');
    return;
  }

  await savePremiumStatus(true, 'pro');
  if (token) {
    await storage.secureSet(IAP_SECURE.productId, productId);
    await storage.secureSet(IAP_SECURE.token, token);
    await storage.secureSet(IAP_SECURE.source, source);
    const deviceId = await authService.getDeviceId();
    if (deviceId) await postEntitlementRegister(deviceId, productId, token, source);
  }

  try {
    await finishNativePurchase(purchase, productId);
  } catch {
    /* store may still finalize */
  }

  void entitlementsService.syncFromServer().then((ent) => {
    monetizationAnalytics.purchaseSuccess(ent.plan);
    monetizationAnalytics.entitlementsLoaded(ent.plan);
  });
  onPurchaseSuccess?.call(null);
}

async function handleStorePurchase(purchase: Purchase): Promise<void> {
  if (purchase.purchaseState === 'pending') return;

  const productId = purchase.productId;
  if (!PRO_PRODUCT_IDS.has(productId)) {
    try {
      await finishNativePurchase(purchase, productId);
    } catch {
      /* ignore */
    }
    return;
  }

  await deliverPurchase(purchase, false);
}

async function verifyPurchasesFromStore(): Promise<void> {
  if (Date.now() - lastVerificationMs < VERIFICATION_COOLDOWN_MS) return;
  lastVerificationMs = Date.now();

  try {
    const restored = await restoreNativePurchases();
    for (const purchase of restored) {
      if (PRO_PRODUCT_IDS.has(purchase.productId)) {
        const { token } = extractPurchaseCredentials(purchase);
        if (token) {
          await deliverPurchase(purchase, false);
        }
        return;
      }
    }
  } catch {
    /* keep local */
  }
}

function priceFromProducts(): string | null {
  const forever = storeProducts.find((p) => p.id === IAP_LIFETIME_LEGACY);
  if (forever) return forever.displayPrice;
  return storeProducts[0]?.displayPrice ?? null;
}

export const purchaseService = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  setPurchaseCallbacks(success: (() => void) | null, error: ((msg: string) => void) | null): void {
    onPurchaseSuccess = success;
    onPurchaseError = error;
  },

  getTier(): AppTier {
    if (debugOverride) return 'pro';
    return tier;
  },

  getStorePrice(): string | null {
    return priceFromProducts();
  },

  getProducts(): StoreProduct[] {
    return storeProducts;
  },

  async isPremium(): Promise<boolean> {
    return isPremium || debugOverride;
  },

  isPremiumSync(): boolean {
    return isPremium || debugOverride;
  },

  async initialize(): Promise<void> {
    if (initialized) return;
    initialized = true;

    await loadLocalPremiumStatus();
    adService.setPremiumStatus(isPremium || debugOverride);

    if (isNativeIapSupported()) {
      const ok = await initNativeIap({
        onPurchase: handleStorePurchase,
        onError: (message) => {
          if (isAlreadyOwnedMessage(message)) {
            void purchaseService.syncEntitlementWithServer().then(() => {
              if (isPremium) onPurchaseSuccess?.call(null);
              else onPurchaseError?.call(null, 'Відновіть покупки в магазині');
            });
            return;
          }
          onPurchaseError?.call(null, message);
        },
      });

      if (ok) {
        storeProducts = await loadNativeProducts();
        void verifyPurchasesFromStore();
      }
    }

    await syncEntitlementWithServerInner();
    await applyDebugPremiumIfNeeded();
    notify();
  },

  async syncEntitlementWithServer(): Promise<void> {
    await syncEntitlementWithServerInner();
    notify();
  },

  async loadProducts(): Promise<StoreProduct[]> {
    if (!isNativeIapSupported()) return [];
    storeProducts = await loadNativeProducts();
    return storeProducts;
  },

  async buyTier(productId: string): Promise<boolean> {
    if (await purchaseService.isPremium()) {
      onPurchaseSuccess?.call(null);
      return true;
    }
    if (storeProducts.length === 0) {
      storeProducts = await loadNativeProducts();
    }
    if (!storeProducts.some((p) => p.id === productId)) {
      onPurchaseError?.call(
        null,
        "Товар недоступний у магазині. Перевірте з'єднання або оновіть додаток.",
      );
      return false;
    }
    const started = await requestNativePurchase(productId);
    if (!started) {
      onPurchaseError?.call(
        null,
        'Не вдалося відкрити оплату. Перевірте інтернет або оновіть сторінку магазину.',
      );
    }
    return started;
  },

  async buyPremium(): Promise<boolean> {
    return purchaseService.buyTier(IAP_LIFETIME_LEGACY);
  },

  async buyProMonthly(): Promise<boolean> {
    return purchaseService.buyTier(IAP_PRO_MONTHLY);
  },

  async buyProPlusMonthly(): Promise<boolean> {
    return purchaseService.buyTier(IAP_PRO_PLUS_MONTHLY);
  },

  async buyMaxMonthly(): Promise<boolean> {
    return purchaseService.buyTier(IAP_MAX_MONTHLY);
  },

  async restorePurchases(): Promise<boolean> {
    if (!isNativeIapSupported()) return false;
    const before = isPremium;
    const restored = await restoreNativePurchases();
    for (const purchase of restored) {
      if (PRO_PRODUCT_IDS.has(purchase.productId)) {
        await deliverPurchase(purchase, false);
        return true;
      }
    }
    return (await purchaseService.isPremium()) || before;
  },

  async enableLocalPro(): Promise<void> {
    if (!__DEV__) return;
    await savePremiumStatus(true, 'pro');
  },

  async disableLocalPro(): Promise<void> {
    await revokePremiumLocal();
  },

  async persistIapCredentials(productId: string, purchaseToken: string, source: string): Promise<void> {
    if (!PRO_PRODUCT_IDS.has(productId)) return;
    await storage.secureSet(IAP_SECURE.productId, productId);
    await storage.secureSet(IAP_SECURE.token, purchaseToken);
    await storage.secureSet(IAP_SECURE.source, source);
    const deviceId = await authService.getDeviceId();
    if (deviceId) await tryBindEntitlementFromStored(deviceId);
  },

  knownProProductIds(): string[] {
    return [...PRO_PRODUCT_IDS];
  },
};

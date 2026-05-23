import { Platform } from 'react-native';
import {
  ErrorCode,
  fetchProducts,
  finishTransaction,
  getAvailablePurchases,
  initConnection,
  purchaseErrorListener,
  purchaseUpdatedListener,
  requestPurchase,
  restorePurchases,
  type Product,
  type Purchase,
} from 'expo-iap';
import {
  IAP_ALL_KNOWN_IDS,
  IAP_LIFETIME_LEGACY,
  IAP_MAX_MONTHLY,
  IAP_PRO_MONTHLY,
  IAP_PRO_PLUS_MONTHLY,
} from '../../monetization/constants/iapProducts';

const IAP_SUBSCRIPTION_SKUS = [IAP_PRO_MONTHLY, IAP_PRO_PLUS_MONTHLY, IAP_MAX_MONTHLY] as const;

export type StoreProduct = {
  id: string;
  displayPrice: string;
  title: string;
};

type Handlers = {
  onPurchase: (purchase: Purchase) => Promise<void>;
  onError: (message: string, code?: string) => void;
};

let connected = false;
let products: StoreProduct[] = [];
let removePurchaseListener: (() => void) | null = null;
let removeErrorListener: (() => void) | null = null;

function isKnownProduct(id: string): boolean {
  return (IAP_ALL_KNOWN_IDS as readonly string[]).includes(id);
}

function purchaseToken(purchase: Purchase): string {
  return String(purchase.purchaseToken ?? '').trim();
}

function purchaseSource(purchase: Purchase): string {
  if (purchase.store === 'apple') return 'app_store';
  if (purchase.store === 'google') return 'google_play';
  return Platform.OS === 'ios' ? 'app_store' : 'google_play';
}

export function getLoadedStoreProducts(): StoreProduct[] {
  return products;
}

export function isNativeIapSupported(): boolean {
  return Platform.OS === 'ios' || Platform.OS === 'android';
}

export async function initNativeIap(handlers: Handlers): Promise<boolean> {
  if (!isNativeIapSupported()) return false;

  removePurchaseListener?.();
  removeErrorListener?.();

  try {
    connected = await initConnection();
    if (!connected) return false;

    removePurchaseListener = purchaseUpdatedListener((purchase) => {
      void handlers.onPurchase(purchase);
    }).remove;

    removeErrorListener = purchaseErrorListener((error) => {
      if (error.code === ErrorCode.UserCancelled) return;
      if (error.code === ErrorCode.AlreadyOwned) {
        handlers.onError('itemAlreadyOwned', error.code);
        return;
      }
      handlers.onError(error.message || 'Помилка покупки', error.code);
    }).remove;

    return true;
  } catch {
    connected = false;
    return false;
  }
}

export async function loadNativeProducts(): Promise<StoreProduct[]> {
  if (!connected) return [];
  try {
    const inApp = await fetchProducts({ skus: [...IAP_ALL_KNOWN_IDS], type: 'in-app' });
    const subs = await fetchProducts({ skus: [...IAP_SUBSCRIPTION_SKUS], type: 'subs' });
    const merged = [...(inApp ?? []), ...(subs ?? [])] as Product[];
    const map = new Map<string, StoreProduct>();
    for (const p of merged) {
      map.set(p.id, {
        id: p.id,
        displayPrice: p.displayPrice,
        title: p.title,
      });
    }
    products = [...map.values()];
    return products;
  } catch {
    products = [];
    return [];
  }
}

function subscriptionOffersFor(product: Product | undefined) {
  if (!product) return undefined;
  const sub = product as Product & {
    subscriptionOffers?: { offerTokenAndroid?: string | null }[];
    subscriptionOfferDetailsAndroid?: { offerToken: string }[];
  };
  const offers =
    sub.subscriptionOffers ??
    sub.subscriptionOfferDetailsAndroid?.map((o) => ({ offerTokenAndroid: o.offerToken }));
  const token = offers?.[0]?.offerTokenAndroid;
  if (!token) return undefined;
  return [{ sku: product.id, offerToken: token }];
}

export async function requestNativePurchase(productId: string): Promise<boolean> {
  if (!connected) return false;
  if (!isKnownProduct(productId)) return false;

  try {
    if ((IAP_SUBSCRIPTION_SKUS as readonly string[]).includes(productId)) {
      const subs = await fetchProducts({ skus: [...IAP_SUBSCRIPTION_SKUS], type: 'subs' });
      const sub = (subs ?? []).find((p) => p.id === productId) as Product | undefined;
      const subscriptionOffers = subscriptionOffersFor(sub);
      await requestPurchase({
        type: 'subs',
        request: {
          apple: { sku: productId },
          google: {
            skus: [productId],
            subscriptionOffers,
          },
        },
      });
      return true;
    }

    await requestPurchase({
      type: 'in-app',
      request: {
        apple: { sku: productId },
        google: { skus: [productId] },
      },
    });
    return true;
  } catch {
    return false;
  }
}

export async function restoreNativePurchases(): Promise<Purchase[]> {
  if (!connected) return [];
  await restorePurchases();
  for (let i = 0; i < 14; i++) {
    await new Promise((r) => setTimeout(r, 350));
  }
  return getAvailablePurchases();
}

export async function finishNativePurchase(purchase: Purchase, productId: string): Promise<void> {
  const consumable = (IAP_SUBSCRIPTION_SKUS as readonly string[]).includes(productId);
  await finishTransaction({ purchase, isConsumable: consumable });
}

export function extractPurchaseCredentials(purchase: Purchase): {
  productId: string;
  token: string;
  source: string;
} {
  return {
    productId: purchase.productId,
    token: purchaseToken(purchase),
    source: purchaseSource(purchase),
  };
}

export function isAlreadyOwnedMessage(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes('alreadyowned') ||
    lower.includes('already owned') ||
    lower.includes('already yours') ||
    lower.includes('уже ваш') ||
    lower.includes('item_already_owned')
  );
}

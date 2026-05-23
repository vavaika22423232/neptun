import { useCallback, useEffect, useState } from 'react';
import { AppConstants } from '../../../config/constants';
import { purchaseService, type AppTier } from '../../../services/purchaseService';

export type PremiumUiState = {
  isPremium: boolean;
  tier: AppTier;
  isLoading: boolean;
  isPurchasing: boolean;
  error: string | null;
  productPrice: string | null;
  showThankYou: boolean;
};

const initial: PremiumUiState = {
  isPremium: false,
  tier: 'free',
  isLoading: true,
  isPurchasing: false,
  error: null,
  productPrice: null,
  showThankYou: false,
};

/** Flutter `premium_provider.dart` parity for paywall screen. */
export function usePremiumStore() {
  const [state, setState] = useState<PremiumUiState>(initial);

  const refreshFromService = useCallback(async () => {
    const premium = await purchaseService.isPremium();
    setState((s) => ({
      ...s,
      isPremium: premium,
      tier: purchaseService.getTier(),
      isLoading: false,
      productPrice: purchaseService.getStorePrice() ?? AppConstants.premiumDisplayPrice,
    }));
  }, []);

  useEffect(() => {
    void refreshFromService();
    const unsub = purchaseService.subscribe(() => {
      void refreshFromService();
    });
    void purchaseService.loadProducts().then(() => {
      setState((s) => ({
        ...s,
        productPrice: purchaseService.getStorePrice() ?? AppConstants.premiumDisplayPrice,
      }));
    });
    return unsub;
  }, [refreshFromService]);

  const buyPremium = useCallback(async () => {
    if (state.isPurchasing) return;
    setState((s) => ({ ...s, isPurchasing: true, error: null }));

    purchaseService.setPurchaseCallbacks(
      () => {
        purchaseService.setPurchaseCallbacks(null, null);
        setState((s) => ({
          ...s,
          isPurchasing: false,
          showThankYou: true,
          isPremium: true,
          tier: 'pro',
        }));
      },
      (msg) => {
        purchaseService.setPurchaseCallbacks(null, null);
        setState((s) => ({ ...s, isPurchasing: false, error: msg }));
      },
    );

    try {
      const started = await purchaseService.buyPremium();
      if (!started) {
        purchaseService.setPurchaseCallbacks(null, null);
        setState((s) => ({
          ...s,
          isPurchasing: false,
          error:
            s.error ??
            'Не вдалося відкрити оплату. Перевірте інтернет або оновіть сторінку магазину.',
        }));
      }
    } catch (e) {
      purchaseService.setPurchaseCallbacks(null, null);
      setState((s) => ({
        ...s,
        isPurchasing: false,
        error: e instanceof Error ? e.message : String(e),
      }));
    }
  }, [state.isPurchasing, state.error]);

  const restorePurchases = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const success = await purchaseService.restorePurchases();
      await refreshFromService();
      setState((s) => ({
        ...s,
        isLoading: false,
        error: success
          ? null
          : 'Активних покупок для цього акаунта App Store / Google Play не знайдено.',
      }));
      return success;
    } catch (e) {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: e instanceof Error ? e.message : String(e),
      }));
      return false;
    }
  }, [refreshFromService]);

  const dismissThankYou = useCallback(() => {
    setState((s) => ({ ...s, showThankYou: false }));
  }, []);

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  return {
    ...state,
    buyPremium,
    restorePurchases,
    dismissThankYou,
    clearError,
    refreshFromService,
  };
}

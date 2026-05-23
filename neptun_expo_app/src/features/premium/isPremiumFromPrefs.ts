import { PrefsKeys } from '../../config/prefsKeys';
import { persistentStorage } from '../../services/persistentStorage';

/** Reads persisted PRO flag without importing `purchaseService` (avoids require cycles). */
export function isPremiumFromPrefs(): boolean {
  if (__DEV__ && persistentStorage.getBoolean(PrefsKeys.debugPremium, false)) {
    return true;
  }
  return persistentStorage.getBoolean(PrefsKeys.isPremium, false);
}

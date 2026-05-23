import * as Linking from 'expo-linking';
import { Platform } from 'react-native';
import { PrefsKeys } from '../config/prefsKeys';
import { AppConstants } from '../config/constants';
import { getExpoStoreReview } from '../utils/lazyExpoNative';
import { persistentStorage } from './persistentStorage';

const DAYS_BEFORE_REVIEW = 3;
const OPENS_BEFORE_REVIEW = 5;

/** Flutter `ReviewService` — in-app review after engagement threshold. */
export const reviewService = {
  async trackAppOpen(): Promise<void> {
    const firstKey = PrefsKeys.reviewFirstLaunchDate;
    if (!persistentStorage.getString(firstKey)) {
      persistentStorage.setString(firstKey, String(Date.now()));
    }

    const count =
      Number(persistentStorage.getString(PrefsKeys.reviewAppLaunchCount) ?? '0') + 1;
    persistentStorage.setString(PrefsKeys.reviewAppLaunchCount, String(count));

    if (persistentStorage.getBoolean(PrefsKeys.reviewHasShownPrompt, false)) return;
    if (count < OPENS_BEFORE_REVIEW) return;

    const installMs = Number(persistentStorage.getString(firstKey) ?? '0');
    if (!installMs) return;
    const days = (Date.now() - installMs) / (24 * 60 * 60 * 1000);
    if (days < DAYS_BEFORE_REVIEW) return;

    const shown = await this.requestReview();
    if (shown) {
      persistentStorage.setBoolean(PrefsKeys.reviewHasShownPrompt, true);
    }
  },

  async requestReview(): Promise<boolean> {
    const StoreReview = getExpoStoreReview();
    if (!StoreReview) return false;
    try {
      if (await StoreReview.isAvailableAsync()) {
        await StoreReview.requestReview();
        return true;
      }
    } catch {
      /* native module missing or store unavailable */
    }
    return false;
  },

  async openStoreListing(): Promise<void> {
    const StoreReview = getExpoStoreReview();
    if (StoreReview) {
      try {
        if (await StoreReview.hasAction()) {
          await StoreReview.requestReview();
          return;
        }
      } catch {
        /* fall through to store URL */
      }
    }
    const url =
      Platform.OS === 'ios' ? AppConstants.appStoreListingUrl : AppConstants.playStoreListingUrl;
    await Linking.openURL(url);
  },
};

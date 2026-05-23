import { isGoogleMobileAdsNativeLinked } from './nativeModuleGuard';

export { isGoogleMobileAdsNativeLinked } from './nativeModuleGuard';

/** Lazy-load AdMob — avoids crash when native module missing, especially on web. */

// Keep this intentionally loose: static type imports from the native ads package
// make Metro traverse native-only files in the web bundle.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type GoogleMobileAdsModule = any;

let cache: GoogleMobileAdsModule | null | undefined;
let requireFailed = false;

export function getGoogleMobileAds(): GoogleMobileAdsModule | null {
  if (requireFailed || !isGoogleMobileAdsNativeLinked()) return null;
  if (cache !== undefined) return cache;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    cache = require('react-native-google-mobile-ads') as GoogleMobileAdsModule;
  } catch {
    requireFailed = true;
    cache = null;
  }
  return cache;
}

export function isGoogleMobileAdsAvailable(): boolean {
  return isGoogleMobileAdsNativeLinked() && getGoogleMobileAds() != null;
}

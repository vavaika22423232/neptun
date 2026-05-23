import { NativeModules, TurboModuleRegistry } from 'react-native';

/** TurboModules throw on `require()` when not linked — probe the registry first. */
export function hasNativeModule(moduleName: string): boolean {
  const legacy = NativeModules[moduleName as keyof typeof NativeModules];
  if (legacy != null) return true;
  try {
    return TurboModuleRegistry.get(moduleName) != null;
  } catch {
    return false;
  }
}

export const NativeModuleNames = {
  googleMobileAds: 'RNGoogleMobileAdsModule',
  firebaseApp: 'RNFBAppModule',
  expoAudio: 'ExpoAudio',
  expoLocation: 'ExpoLocation',
} as const;

export function isExpoAudioNativeLinked(): boolean {
  return hasNativeModule(NativeModuleNames.expoAudio);
}

export function isExpoLocationNativeLinked(): boolean {
  return hasNativeModule(NativeModuleNames.expoLocation);
}

export function isGoogleMobileAdsNativeLinked(): boolean {
  return hasNativeModule(NativeModuleNames.googleMobileAds);
}

export function isFirebaseNativeLinked(): boolean {
  return hasNativeModule(NativeModuleNames.firebaseApp);
}

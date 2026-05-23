/**
 * Lazy-load Expo native modules so JS bundles work before a dev-client rebuild.
 * After adding native modules: `npx expo prebuild && npx expo run:ios`.
 */
import { requireOptionalNativeModule } from 'expo-modules-core';

type SpeechModule = typeof import('expo-speech');
type HapticsModule = typeof import('expo-haptics');
type StoreReviewModule = typeof import('expo-store-review');

let speechCache: SpeechModule | null | undefined;
let speechFailed = false;
let speechNativeChecked = false;
let speechNativePresent = false;

let hapticsCache: HapticsModule | null | undefined;
let hapticsFailed = false;
let hapticsNativeChecked = false;
let hapticsNativePresent = false;

let storeReviewCache: StoreReviewModule | null | undefined;
let storeReviewFailed = false;
let storeReviewNativeChecked = false;
let storeReviewNativePresent = false;

function probeNativeModule(name: string): boolean {
  try {
    return requireOptionalNativeModule(name) != null;
  } catch {
    return false;
  }
}

function ensureSpeechNative(): boolean {
  if (speechNativeChecked) return speechNativePresent;
  speechNativeChecked = true;
  speechNativePresent = probeNativeModule('ExpoSpeech');
  if (!speechNativePresent) {
    speechFailed = true;
    speechCache = null;
  }
  return speechNativePresent;
}

export function getExpoSpeech(): SpeechModule | null {
  if (speechFailed) return null;
  if (!ensureSpeechNative()) return null;
  if (speechCache !== undefined) return speechCache;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    speechCache = require('expo-speech') as SpeechModule;
  } catch {
    speechFailed = true;
    speechCache = null;
  }
  return speechCache;
}

export function isExpoSpeechAvailable(): boolean {
  return ensureSpeechNative() && getExpoSpeech() != null;
}

function ensureHapticsNative(): boolean {
  if (hapticsNativeChecked) return hapticsNativePresent;
  hapticsNativeChecked = true;
  // expo-haptics iOS module name
  hapticsNativePresent = probeNativeModule('ExpoHaptics');
  if (!hapticsNativePresent) {
    hapticsFailed = true;
    hapticsCache = null;
  }
  return hapticsNativePresent;
}

export function getExpoHaptics(): HapticsModule | null {
  if (hapticsFailed) return null;
  if (!ensureHapticsNative()) return null;
  if (hapticsCache !== undefined) return hapticsCache;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    hapticsCache = require('expo-haptics') as HapticsModule;
  } catch {
    hapticsFailed = true;
    hapticsCache = null;
  }
  return hapticsCache;
}

export function isExpoHapticsAvailable(): boolean {
  return ensureHapticsNative() && getExpoHaptics() != null;
}

function markHapticsUnavailable(): void {
  hapticsFailed = true;
  hapticsCache = null;
}

/** UI tap feedback — no-op if native module missing (stale dev client). */
export function voidHapticImpact(style: 'light' | 'medium' | 'heavy' = 'light'): void {
  if (hapticsFailed) return;
  const Haptics = getExpoHaptics();
  if (!Haptics) return;
  const styleMap = {
    light: Haptics.ImpactFeedbackStyle.Light,
    medium: Haptics.ImpactFeedbackStyle.Medium,
    heavy: Haptics.ImpactFeedbackStyle.Heavy,
  };
  void Haptics.impactAsync(styleMap[style]).catch(() => {
    markHapticsUnavailable();
  });
}

function ensureStoreReviewNative(): boolean {
  if (storeReviewNativeChecked) return storeReviewNativePresent;
  storeReviewNativeChecked = true;
  storeReviewNativePresent = probeNativeModule('ExpoStoreReview');
  if (!storeReviewNativePresent) {
    storeReviewFailed = true;
    storeReviewCache = null;
  }
  return storeReviewNativePresent;
}

export function getExpoStoreReview(): StoreReviewModule | null {
  if (storeReviewFailed) return null;
  if (!ensureStoreReviewNative()) return null;
  if (storeReviewCache !== undefined) return storeReviewCache;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    storeReviewCache = require('expo-store-review') as StoreReviewModule;
  } catch {
    storeReviewFailed = true;
    storeReviewCache = null;
  }
  return storeReviewCache;
}

export function isExpoStoreReviewAvailable(): boolean {
  return ensureStoreReviewNative() && getExpoStoreReview() != null;
}

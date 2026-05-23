import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as IntentLauncher from 'expo-intent-launcher';
import { Linking, Platform } from 'react-native';
import { PrefsKeys } from '../config/prefsKeys';
import { persistentStorage } from './persistentStorage';

const PROMPT_COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000;

function brandLower(): string {
  return (Device.brand ?? Device.manufacturer ?? '').toLowerCase();
}

/** Flutter `AndroidPlatformService.needsBatteryOptimizationWarning`. */
export function needsBatteryOptimizationWarning(): boolean {
  if (Platform.OS !== 'android') return false;
  const b = brandLower();
  return (
    b.includes('xiaomi') ||
    b.includes('redmi') ||
    b.includes('poco') ||
    b.includes('huawei') ||
    b.includes('honor')
  );
}

/** Flutter `AppShell._maybeShowBatteryOptPrompt` — show at most once per 7 days. */
export function shouldShowBatteryOptPrompt(): boolean {
  if (!needsBatteryOptimizationWarning()) return false;
  const last = Number(persistentStorage.getString(PrefsKeys.batteryOptPromptLastShown) ?? '0');
  return Date.now() - last >= PROMPT_COOLDOWN_MS;
}

export function markBatteryOptPromptShown(): void {
  persistentStorage.setString(PrefsKeys.batteryOptPromptLastShown, String(Date.now()));
}

/** Open system UI to disable battery optimization (best-effort). */
export async function requestDisableBatteryOptimization(): Promise<void> {
  if (Platform.OS !== 'android') return;
  try {
    await IntentLauncher.startActivityAsync(
      'android.settings.IGNORE_BATTERY_OPTIMIZATION_SETTINGS' as IntentLauncher.ActivityAction,
    );
    return;
  } catch {
    /* fall through */
  }
  try {
    const pkg =
      Constants.expoConfig?.android?.package ?? 'com.neptunalarm.neptun_alarm_app';
    await IntentLauncher.startActivityAsync(IntentLauncher.ActivityAction.APPLICATION_DETAILS_SETTINGS, {
      data: `package:${pkg}`,
    });
    return;
  } catch {
    await Linking.openSettings();
  }
}

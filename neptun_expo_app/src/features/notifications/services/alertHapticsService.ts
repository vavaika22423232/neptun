import { Platform } from 'react-native';
import { PrefsKeys } from '../../../config/prefsKeys';
import { getExpoHaptics } from '../../../utils/lazyExpoNative';
import { persistentStorage } from '../../../services/persistentStorage';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Flutter `_vibrateForAlert` patterns. */
export async function vibrateForAlert(text: string): Promise<void> {
  if (Platform.OS === 'web') return;
  if (!persistentStorage.getBoolean(PrefsKeys.vibrationEnabled, true)) return;

  const Haptics = getExpoHaptics();
  if (!Haptics) return;

  const lower = text.toLowerCase();

  try {
    if (lower.includes('відбій')) {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      await sleep(150);
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      return;
    }

    if (lower.includes('ракет') || lower.includes('балістичн')) {
      for (let i = 0; i < 3; i += 1) {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        await sleep(100);
      }
      await sleep(200);
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      return;
    }

    if (lower.includes('бпла') || lower.includes('дрон')) {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      await sleep(120);
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      return;
    }

    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  } catch {
    /* haptics unavailable */
  }
}

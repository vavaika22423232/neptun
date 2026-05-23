import * as Linking from 'expo-linking';
import { AppConstants } from '../../config/constants';
import { analyticsService } from '../../services/analyticsService';

/** Flutter `open_neptun_telegram.dart` — log CTA source then open invite link. */
export async function openNeptunTelegramChannel(source: string): Promise<boolean> {
  void analyticsService.logEvent('telegram_cta_tap', { source });
  try {
    const can = await Linking.canOpenURL(AppConstants.telegramUrl);
    if (!can) return false;
    await Linking.openURL(AppConstants.telegramUrl);
    return true;
  } catch {
    return false;
  }
}

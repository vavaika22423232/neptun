import Constants from 'expo-constants';
import { API_BASE_URL } from './api';
import { AppConstants } from './constants';
import { TELEGRAM_CHANNEL_URL } from './links';

const extra = Constants.expoConfig?.extra as Record<string, unknown> | undefined;

/** Central feature/config flags — single source for env-driven behavior. */
export const appConfig = {
  apiBaseUrl: API_BASE_URL,
  telegramUrl: TELEGRAM_CHANNEL_URL,
  supportUrl: (extra?.supportUrl as string | undefined) ?? 'https://neptun.in.ua/support',
  privacyUrl: (extra?.privacyUrl as string | undefined) ?? 'https://neptun.in.ua/privacy',
  termsUrl: (extra?.termsUrl as string | undefined) ?? 'https://neptun.in.ua/terms',
  websiteUrl: 'https://neptun.in.ua',
  adsEnabled: extra?.adsEnabled !== false,
  proEnabled: extra?.proEnabled !== false,
  debugMode: __DEV__ || process.env.EXPO_PUBLIC_DEBUG === 'true',
  appName: AppConstants.appName,
  appVersion: AppConstants.appVersion,
} as const;

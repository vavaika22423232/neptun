import type { PlanId } from './plans';
import { buildFeatures } from './plans';

export type MonetizationConfigPayload = {
  enableProPaywall: boolean;
  enableProPlus: boolean;
  enableMaxPlan: boolean;
  enableSmartNotifications: boolean;
  enableMyRadar: boolean;
  enableHistoryAnalytics: boolean;
  enableExtendedThreatCard: boolean;
  enableTelegramAdminMode: boolean;
  enableDailyReports: boolean;
  enableWeeklyReports: boolean;
  enableRewardedAdFree: boolean;
  enablePremiumMap: boolean;
  enableCustomSounds: boolean;
  enableQuietMode: boolean;
  enableServerEntitlements: boolean;
  plans: {
    id: PlanId;
    priceUah: number;
    label: string;
    productIds: { google: string; apple: string };
    features: ReturnType<typeof buildFeatures>;
  }[];
  limits: {
    free: { historyDays: number; myRadarLocations: number; notificationRules: number };
    pro: { historyDays: number; myRadarLocations: number; notificationRules: number };
    pro_plus: { historyDays: number; myRadarLocations: number; notificationRules: number };
    max: { historyDays: number; myRadarLocations: number; notificationRules: number };
  };
  paywall: {
    title: string;
    subtitle: string;
    proPlusBadge: string;
    maxBadge: string;
  };
  rewarded: {
    adFreeHours: number;
    historyUnlockHours: number;
  };
};

export function getMonetizationConfig(): MonetizationConfigPayload {
  return {
    enableProPaywall: process.env.MONETIZATION_ENABLE_PAYWALL !== 'false',
    enableProPlus: process.env.MONETIZATION_ENABLE_PRO_PLUS !== 'false',
    enableMaxPlan: process.env.MONETIZATION_ENABLE_MAX !== 'false',
    enableSmartNotifications: process.env.MONETIZATION_ENABLE_SMART_NOTIFICATIONS !== 'false',
    enableMyRadar: process.env.MONETIZATION_ENABLE_MY_RADAR !== 'false',
    enableHistoryAnalytics: process.env.MONETIZATION_ENABLE_HISTORY !== 'false',
    enableExtendedThreatCard: process.env.MONETIZATION_ENABLE_THREAT_CARD !== 'false',
    enableTelegramAdminMode: process.env.MONETIZATION_ENABLE_TELEGRAM_ADMIN !== 'false',
    enableDailyReports: process.env.MONETIZATION_ENABLE_DAILY_REPORTS !== 'false',
    enableWeeklyReports: process.env.MONETIZATION_ENABLE_WEEKLY_REPORTS !== 'false',
    enableRewardedAdFree: process.env.MONETIZATION_ENABLE_REWARDED !== 'false',
    enablePremiumMap: process.env.MONETIZATION_ENABLE_PREMIUM_MAP !== 'false',
    enableCustomSounds: process.env.MONETIZATION_ENABLE_CUSTOM_SOUNDS !== 'false',
    enableQuietMode: process.env.MONETIZATION_ENABLE_QUIET_MODE !== 'false',
    enableServerEntitlements: process.env.MONETIZATION_ENABLE_SERVER_ENTITLEMENTS !== 'false',
    plans: [
      {
        id: 'pro',
        priceUah: 69,
        label: 'PRO',
        productIds: { google: 'neptun_pro_monthly_69', apple: 'neptun_pro_monthly_69' },
        features: buildFeatures('pro'),
      },
      {
        id: 'pro_plus',
        priceUah: 129,
        label: 'PRO+',
        productIds: { google: 'neptun_pro_plus_monthly_129', apple: 'neptun_pro_plus_monthly_129' },
        features: buildFeatures('pro_plus'),
      },
      {
        id: 'max',
        priceUah: 199,
        label: 'MAX',
        productIds: { google: 'neptun_max_monthly_199', apple: 'neptun_max_monthly_199' },
        features: buildFeatures('max'),
      },
    ],
    limits: {
      free: { historyDays: 1, myRadarLocations: 0, notificationRules: 0 },
      pro: { historyDays: 7, myRadarLocations: 3, notificationRules: 3 },
      pro_plus: { historyDays: 30, myRadarLocations: 10, notificationRules: 10 },
      max: { historyDays: 90, myRadarLocations: 30, notificationRules: 30 },
    },
    paywall: {
      title: 'Більше контролю під час тривог',
      subtitle:
        'PRO відкриває розумні сповіщення, історію, персональний радар, аналітику та вимикає рекламу. Базова карта й важливі сповіщення залишаються безкоштовними.',
      proPlusBadge: 'Популярний',
      maxBadge: 'Для адмінів, медіа та тих, хто слідкує постійно',
    },
    rewarded: {
      adFreeHours: 4,
      historyUnlockHours: 24,
    },
  };
}

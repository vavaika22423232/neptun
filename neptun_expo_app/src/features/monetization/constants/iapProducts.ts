/** Store product IDs — must match Play Console / App Store Connect + backend PRODUCT_TO_PLAN */

export const IAP_PRO_MONTHLY = 'neptun_pro_monthly_69';
export const IAP_PRO_PLUS_MONTHLY = 'neptun_pro_plus_monthly_129';
export const IAP_MAX_MONTHLY = 'neptun_max_monthly_199';

/** Legacy lifetime PRO — keep for restore; maps to pro_plus entitlements server-side */
export const IAP_LIFETIME_LEGACY = 'premium_150_uah';

export const IAP_LEGACY_PRO_IDS = [
  'premium_100_uah',
  'premium',
  'com.neptunalarm.premium',
  'pro_monthly',
] as const;

export const IAP_ALL_KNOWN_IDS = [
  IAP_PRO_MONTHLY,
  IAP_PRO_PLUS_MONTHLY,
  IAP_MAX_MONTHLY,
  IAP_LIFETIME_LEGACY,
  ...IAP_LEGACY_PRO_IDS,
] as const;

export type IapProductId = (typeof IAP_ALL_KNOWN_IDS)[number];

export const PLAN_PRICES_UAH = {
  pro: 69,
  pro_plus: 129,
  max: 199,
} as const;

/**
 * Monetization plan catalog — single source of truth for server-side entitlements.
 */

export type PlanId = 'free' | 'pro' | 'pro_plus' | 'max' | 'lifetime';

export type SubscriptionStatus =
  | 'active'
  | 'expired'
  | 'cancelled'
  | 'grace_period'
  | 'billing_retry'
  | 'unknown';

export type EntitlementFeatures = {
  adsDisabled: boolean;
  smartNotifications: boolean;
  historyDays: number;
  myRadarLocationsLimit: number;
  advancedAnalytics: boolean;
  telegramAdminMode: boolean;
  exportReports: boolean;
  premiumMap: boolean;
  customSounds: boolean;
  quietMode: boolean;
  extendedThreatCard: boolean;
  dailyReports: boolean;
  weeklyReports: boolean;
  threatTypeFilters: boolean;
  notificationRulesLimit: number;
};

export const PLAN_RANK: Record<PlanId, number> = {
  free: 0,
  pro: 1,
  pro_plus: 2,
  max: 3,
  lifetime: 2, // lifetime ≈ PRO+ perks for ads/history; maps to pro_plus features
};

/** Monthly subscription + legacy lifetime SKUs */
export const PRODUCT_TO_PLAN: Record<string, PlanId> = {
  neptun_pro_monthly_69: 'pro',
  neptun_pro_plus_monthly_129: 'pro_plus',
  neptun_max_monthly_199: 'max',
  pro_monthly: 'pro', // legacy client SKU → treat as PRO until stores updated
  premium_150_uah: 'lifetime',
  premium_100_uah: 'lifetime',
  premium: 'lifetime',
  'com.neptunalarm.premium': 'lifetime',
};

export const ALL_KNOWN_PRODUCT_IDS = Object.keys(PRODUCT_TO_PLAN);

export function planFromProductId(productId: string): PlanId {
  return PRODUCT_TO_PLAN[productId] ?? 'free';
}

export function isPaidPlan(plan: PlanId): boolean {
  return plan !== 'free';
}

export function maxPlan(a: PlanId, b: PlanId): PlanId {
  return PLAN_RANK[a] >= PLAN_RANK[b] ? a : b;
}

export function buildFeatures(plan: PlanId): EntitlementFeatures {
  switch (plan) {
    case 'max':
      return {
        adsDisabled: true,
        smartNotifications: true,
        historyDays: 90,
        myRadarLocationsLimit: 30,
        advancedAnalytics: true,
        telegramAdminMode: true,
        exportReports: true,
        premiumMap: true,
        customSounds: true,
        quietMode: true,
        extendedThreatCard: true,
        dailyReports: true,
        weeklyReports: true,
        threatTypeFilters: true,
        notificationRulesLimit: 30,
      };
    case 'pro_plus':
    case 'lifetime':
      return {
        adsDisabled: true,
        smartNotifications: true,
        historyDays: plan === 'lifetime' ? 30 : 30,
        myRadarLocationsLimit: 10,
        advancedAnalytics: true,
        telegramAdminMode: false,
        exportReports: false,
        premiumMap: true,
        customSounds: true,
        quietMode: true,
        extendedThreatCard: true,
        dailyReports: true,
        weeklyReports: true,
        threatTypeFilters: true,
        notificationRulesLimit: 10,
      };
    case 'pro':
      return {
        adsDisabled: true,
        smartNotifications: true,
        historyDays: 7,
        myRadarLocationsLimit: 3,
        advancedAnalytics: false,
        telegramAdminMode: false,
        exportReports: false,
        premiumMap: true,
        customSounds: true,
        quietMode: true,
        extendedThreatCard: false,
        dailyReports: true,
        weeklyReports: false,
        threatTypeFilters: false,
        notificationRulesLimit: 3,
      };
    default:
      return {
        adsDisabled: false,
        smartNotifications: false,
        historyDays: 1,
        myRadarLocationsLimit: 0,
        advancedAnalytics: false,
        telegramAdminMode: false,
        exportReports: false,
        premiumMap: false,
        customSounds: false,
        quietMode: false,
        extendedThreatCard: false,
        dailyReports: false,
        weeklyReports: false,
        threatTypeFilters: false,
        notificationRulesLimit: 0,
      };
  }
}

export type EntitlementsPayload = {
  plan: PlanId;
  isPro: boolean;
  expiresAt: string | null;
  features: EntitlementFeatures;
  status: SubscriptionStatus;
  productId: string | null;
};

export function buildEntitlements(
  plan: PlanId,
  opts?: { expiresAt?: string | null; status?: SubscriptionStatus; productId?: string | null },
): EntitlementsPayload {
  const effective = plan === 'lifetime' ? 'pro_plus' : plan;
  return {
    plan: effective,
    isPro: isPaidPlan(plan),
    expiresAt: opts?.expiresAt ?? (plan === 'lifetime' ? null : null),
    features: buildFeatures(plan),
    status: opts?.status ?? (isPaidPlan(plan) ? 'active' : 'unknown'),
    productId: opts?.productId ?? null,
  };
}

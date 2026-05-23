export type PlanId = 'free' | 'pro' | 'pro_plus' | 'max';

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

export type EntitlementsPayload = {
  plan: PlanId;
  isPro: boolean;
  expiresAt: string | null;
  features: EntitlementFeatures;
  status: SubscriptionStatus;
  productId: string | null;
};

export const FREE_ENTITLEMENTS: EntitlementsPayload = {
  plan: 'free',
  isPro: false,
  expiresAt: null,
  status: 'unknown',
  productId: null,
  features: {
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
  },
};

export const PLAN_RANK: Record<PlanId, number> = {
  free: 0,
  pro: 1,
  pro_plus: 2,
  max: 3,
};

export function hasMinPlan(current: PlanId, required: PlanId): boolean {
  return PLAN_RANK[current] >= PLAN_RANK[required];
}

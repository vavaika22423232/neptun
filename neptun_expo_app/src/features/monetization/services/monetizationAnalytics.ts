import { analyticsService } from '../../../services/analyticsService';
import type { PlanId } from '../types';

function log(event: string, params?: Record<string, string | number | boolean>): void {
  void analyticsService.logEvent(event, params);
}

export const monetizationAnalytics = {
  paywallOpened(source: string) {
    log('paywall_opened', { source });
  },
  paywallClosed() {
    log('paywall_closed');
  },
  paywallPlanSelected(plan: PlanId) {
    log('paywall_plan_selected', { plan });
  },
  purchaseStarted(plan: PlanId, productId: string) {
    log('purchase_started', { plan, product_id: productId });
  },
  purchaseSuccess(plan: PlanId) {
    log('purchase_success', { plan });
  },
  purchaseFailed(reason: string) {
    log('purchase_failed', { reason });
  },
  restoreClicked() {
    log('restore_purchases_clicked');
  },
  restoreSuccess(plan: PlanId) {
    log('restore_purchases_success', { plan });
  },
  entitlementsLoaded(plan: PlanId) {
    log('entitlements_loaded', { plan });
  },
  entitlementsFailed() {
    log('entitlements_failed');
  },
  featureLockedClicked(feature: string, requiredPlan: PlanId) {
    log('feature_locked_clicked', { feature, required_plan: requiredPlan });
  },
  adSkippedBecausePaid() {
    log('ad_skipped_because_paid');
  },
  adShown(placement: string) {
    log('ad_shown', { placement });
  },
  rewardedStarted(kind: string) {
    log('rewarded_started', { kind });
  },
  rewardedCompleted(kind: string) {
    log('rewarded_completed', { kind });
  },
  temporaryAdFreeStarted(hours: number) {
    log('temporary_ad_free_started', { hours });
  },
  smartNotificationsOpened(plan?: PlanId) {
    log('smart_notifications_opened', plan ? { plan } : undefined);
  },
  notificationRuleCreated(plan?: PlanId) {
    log('notification_rule_created', plan ? { plan } : undefined);
  },
  notificationRuleUpdated(plan?: PlanId) {
    log('notification_rule_updated', plan ? { plan } : undefined);
  },
  quietModeEnabled(enabled: boolean) {
    log('quiet_mode_enabled', { enabled });
  },
  myRadarOpened(plan?: PlanId) {
    log('my_radar_opened', plan ? { plan } : undefined);
  },
  myRadarLocationAdded(plan?: PlanId) {
    log('my_radar_location_added', plan ? { plan } : undefined);
  },
  myRadarLimitReached(plan?: PlanId) {
    log('my_radar_limit_reached', plan ? { plan } : undefined);
  },
  historyOpened(plan?: PlanId, maxDays?: number) {
    log('history_opened', { ...(plan ? { plan } : {}), ...(maxDays != null ? { max_days: maxDays } : {}) });
  },
  historyFilterUsed(kind: string) {
    log('history_filter_used', { kind });
  },
  weeklyReportOpened(plan?: PlanId) {
    log('weekly_report_opened', plan ? { plan } : undefined);
  },
  historyRangeLocked(plan?: PlanId, maxDays?: number) {
    log('history_range_locked', { ...(plan ? { plan } : {}), ...(maxDays != null ? { max_days: maxDays } : {}) });
  },
  dailyReportOpened(plan?: PlanId) {
    log('daily_report_opened', plan ? { plan } : undefined);
  },
  telegramAdminOpened(plan?: PlanId) {
    log('telegram_admin_opened', plan ? { plan } : undefined);
  },
  telegramSummaryGenerated(templateId: string) {
    log('telegram_summary_generated', { template_id: templateId });
  },
  telegramSummaryCopied(templateId: string) {
    log('telegram_summary_copied', { template_id: templateId });
  },
};

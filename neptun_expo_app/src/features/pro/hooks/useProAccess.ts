import { useRouter } from 'expo-router';
import { useCallback } from 'react';
import { useApp } from '../../../context/AppContext';
import { useEntitlements } from '../../monetization/hooks/useEntitlements';
import { monetizationAnalytics } from '../../monetization/services/monetizationAnalytics';
import type { PlanId } from '../../monetization/types';
import {
  analyticsSource,
  LOCKED_FEATURES,
  type LockedFeatureId,
  type ProEntrySource,
} from '../utils/proFeatures';

export function useProAccess() {
  const router = useRouter();
  const { isPremium } = useApp();
  const { entitlements, plan, hasPlan, features, refresh } = useEntitlements();

  const openPaywall = useCallback(
    (opts?: { source?: ProEntrySource; lockedFeature?: LockedFeatureId }) => {
      const source = analyticsSource(opts?.source ?? 'profile', opts?.lockedFeature);
      if (opts?.lockedFeature) {
        const spec = LOCKED_FEATURES[opts.lockedFeature];
        monetizationAnalytics.featureLockedClicked(spec.label, spec.minPlan);
      }
      router.push({
        pathname: '/premium',
        params: {
          source,
          ...(opts?.lockedFeature ? { feature: opts.lockedFeature } : {}),
        },
      });
    },
    [router],
  );

  const canAccess = useCallback(
    (minPlan: PlanId) => hasPlan(minPlan),
    [hasPlan],
  );

  return {
    isPremium,
    isPaid: entitlements.isPro,
    plan,
    features,
    entitlements,
    hasPlan,
    canAccess,
    openPaywall,
    refresh,
  };
}

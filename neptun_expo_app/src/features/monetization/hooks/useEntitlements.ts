import { useCallback, useEffect, useState } from 'react';
import type { EntitlementsPayload, PlanId } from '../types';
import { hasMinPlan, FREE_ENTITLEMENTS } from '../types';
import { entitlementsService } from '../../../services/entitlementsService';

export function useEntitlements() {
  const [entitlements, setEntitlements] = useState<EntitlementsPayload>(
    entitlementsService.getCached() ?? FREE_ENTITLEMENTS,
  );

  useEffect(() => {
    const unsub = entitlementsService.subscribe(() => {
      setEntitlements(entitlementsService.getCached());
    });
    return unsub;
  }, []);

  const hasPlan = useCallback((min: PlanId) => hasMinPlan(entitlements.plan, min), [entitlements.plan]);

  return {
    entitlements,
    plan: entitlements.plan,
    isPaid: entitlements.isPro,
    features: entitlements.features,
    hasPlan,
    refresh: () => entitlementsService.syncFromServer(),
  };
}

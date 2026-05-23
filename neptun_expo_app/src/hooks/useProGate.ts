import { ProFeature, ProGate } from '../core/pro/proGate';
import { useApp } from '../context/AppContext';

export function useProGate(feature: ProFeature): { unlocked: boolean; loading: boolean } {
  const { isPremium } = useApp();
  return {
    unlocked: ProGate.isUnlockedSync(feature, isPremium),
    loading: false,
  };
}

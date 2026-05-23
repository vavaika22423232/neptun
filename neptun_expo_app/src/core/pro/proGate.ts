import { purchaseService } from '../../services/purchaseService';
import {
  isProFeatureUnlockedSync,
  ProFeature,
  proFeatureNames,
  PRO_ONLY_FEATURES,
} from './proFeatureCatalog';

export { ProFeature, proFeatureNames } from './proFeatureCatalog';

export const ProGate = {
  async isPro(): Promise<boolean> {
    return purchaseService.isPremium();
  },

  async mapThreatHistoryMinutes(): Promise<number> {
    return (await purchaseService.isPremium()) ? 120 : 30;
  },

  async isUnlocked(feature: ProFeature): Promise<boolean> {
    if (await purchaseService.isPremium()) return true;
    return !PRO_ONLY_FEATURES.has(feature);
  },

  isUnlockedSync(feature: ProFeature, isPremium: boolean): boolean {
    return isProFeatureUnlockedSync(feature, isPremium);
  },
};

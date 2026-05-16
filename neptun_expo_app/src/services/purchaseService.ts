import { storage } from './storage';

export type AppTier = 'free' | 'pro';

export const purchaseService = {
  async isPremium(): Promise<boolean> {
    return storage.isPremium();
  },

  async enableLocalPro(): Promise<void> {
    await storage.setPremium(true);
  },

  async disableLocalPro(): Promise<void> {
    await storage.setPremium(false);
  },
};

import { useEffect, useState } from 'react';
import { changelogForCurrentVersion } from '../config/changelog';
import { changelogService } from '../services/changelogService';
import {
  markBatteryOptPromptShown,
  requestDisableBatteryOptimization,
  shouldShowBatteryOptPrompt,
} from '../services/batteryOptimizationService';
import { reviewService } from '../services/reviewService';

/**
 * Post-onboarding engagement: changelog, battery opt (Android Xiaomi/Huawei), in-app review.
 */
export function useAppEngagementModals(enabled: boolean) {
  const [changelogVisible, setChangelogVisible] = useState(false);
  const [batteryVisible, setBatteryVisible] = useState(false);

  useEffect(() => {
    if (!enabled) return;

    void reviewService.trackAppOpen();

    if (changelogService.shouldShow()) {
      setChangelogVisible(true);
    } else if (shouldShowBatteryOptPrompt()) {
      markBatteryOptPromptShown();
      setBatteryVisible(true);
    }
  }, [enabled]);

  const dismissChangelog = () => {
    changelogService.markShown();
    setChangelogVisible(false);
    if (shouldShowBatteryOptPrompt()) {
      markBatteryOptPromptShown();
      setBatteryVisible(true);
    }
  };

  const dismissBattery = () => setBatteryVisible(false);

  const openBatterySettings = () => {
    setBatteryVisible(false);
    void requestDisableBatteryOptimization();
  };

  return {
    changelogVisible,
    changelogItems: changelogForCurrentVersion(),
    dismissChangelog,
    batteryVisible,
    dismissBattery,
    openBatterySettings,
  };
}

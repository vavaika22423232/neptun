import { PrefsKeys } from '../config/prefsKeys';
import { persistentStorage } from './persistentStorage';

/** Flutter `PersonalAnalyticsPage._loadStats` region label. */
export function getAnalyticsRegionLabel(): string {
  const selected = persistentStorage.getStringList(PrefsKeys.selectedRegions);
  const oblasts = selected.filter((r) => r.includes('область') || r.includes('місто'));

  if (oblasts.length === 0) {
    return persistentStorage.getString('onboarding_region') ?? 'Невизначено';
  }
  if (oblasts.length === 1) return oblasts[0];
  return `${oblasts.length} регіонів`;
}

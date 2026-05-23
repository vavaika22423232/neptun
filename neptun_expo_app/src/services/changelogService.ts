import { AppConstants } from '../config/constants';
import { changelogForCurrentVersion } from '../config/changelog';
import { PrefsKeys } from '../config/prefsKeys';
import { persistentStorage } from './persistentStorage';

/** Flutter `ChangelogDialog.showIfNeeded`. */
export const changelogService = {
  shouldShow(): boolean {
    const items = changelogForCurrentVersion();
    if (items.length === 0) return false;
    const last = persistentStorage.getString(PrefsKeys.changelogLastShownVersion);
    return last !== AppConstants.appVersion;
  },

  markShown(): void {
    persistentStorage.setString(PrefsKeys.changelogLastShownVersion, AppConstants.appVersion);
  },
};

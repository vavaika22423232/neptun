import { PrefsKeys } from '../config/prefsKeys';
import { persistentStorage } from '../services/persistentStorage';
import type { ThemeMode } from './types';
import { isThemeMode } from './themeMode';

export { isThemeMode } from './themeMode';

/** Read persisted preference; migrates legacy boolean dark toggle. */
export function loadThemeMode(): ThemeMode {
  const stored = persistentStorage.getString(PrefsKeys.themeMode);
  if (isThemeMode(stored)) return stored;

  const legacyDark = persistentStorage.getBoolean(PrefsKeys.darkMode, true);
  const migrated: ThemeMode = legacyDark ? 'dark' : 'light';
  persistentStorage.setString(PrefsKeys.themeMode, migrated);
  return migrated;
}

export function saveThemeMode(mode: ThemeMode): void {
  persistentStorage.setString(PrefsKeys.themeMode, mode);
}

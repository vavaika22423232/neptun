import { Appearance } from 'react-native';
import { createAppTheme } from './theme';
import { loadThemeMode } from './themeStorage';
import type { AppTheme, ResolvedScheme, ThemeMode } from './types';

function resolveBootScheme(mode: ThemeMode): ResolvedScheme {
  if (mode === 'light') return 'light';
  if (mode === 'dark') return 'dark';
  return Appearance.getColorScheme() === 'light' ? 'light' : 'dark';
}

/** Sync boot theme so legacy module StyleSheets resolve the saved scheme on first import. */
let activeTheme: AppTheme = createAppTheme(resolveBootScheme(loadThemeMode()));

export function getActiveTheme(): AppTheme {
  return activeTheme;
}

export function setActiveTheme(theme: AppTheme): void {
  activeTheme = theme;
}

/**
 * Design system entry — layout tokens are static; colors follow ThemeProvider.
 * Prefer `useAppTheme()` / `useLegacyPalette()` in components.
 */
import { getActiveTheme } from '../theme/activeTheme';
import { motion, radii, spacing, typography } from '../theme/tokens';
import type { AppTheme, LegacyPalette, ProfileThemeTokens, ThemeShadows } from '../theme/types';

export { motion, radii, spacing, typography };

/** @deprecated Use `useLegacyPalette()` — reads active theme on each property access. */
export const palette = new Proxy({} as LegacyPalette, {
  get(_t, prop: string | symbol) {
    return getActiveTheme().palette[prop as keyof LegacyPalette];
  },
});

export const shadows = new Proxy({} as ThemeShadows, {
  get(_t, prop: string | symbol) {
    return getActiveTheme().shadows[prop as keyof ThemeShadows];
  },
});

export const glass = new Proxy({} as AppTheme['glass'], {
  get(_t, prop: string | symbol) {
    return getActiveTheme().glass[prop as keyof AppTheme['glass']];
  },
});

export const profile = new Proxy({} as ProfileThemeTokens, {
  get(_t, prop: string | symbol) {
    return getActiveTheme().profile[prop as keyof ProfileThemeTokens];
  },
});

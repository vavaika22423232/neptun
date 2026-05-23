/**
 * Legacy color map — reads from active theme (see ThemeProvider).
 * Prefer `useLegacyColors()` in new components.
 */
import { getActiveTheme } from './activeTheme';
import type { LegacyColors } from './types';
import { radii, spacing } from './tokens';

export const colors = new Proxy({} as LegacyColors, {
  get(_target, prop: keyof LegacyColors) {
    return getActiveTheme().legacyColors[prop];
  },
});

export { radii, spacing };

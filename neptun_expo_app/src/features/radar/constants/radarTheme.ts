import { getActiveTheme } from '../../../theme/activeTheme';
import type { RadarThemeTokens } from '../../../theme/types';

/** @deprecated Use `useRadarTheme()` from `src/theme/useAppTheme`. */
export const radarTheme = new Proxy({} as RadarThemeTokens, {
  get(_t, prop: keyof RadarThemeTokens) {
    return getActiveTheme().radar[prop];
  },
});

export { useRadarTheme } from '../../../theme/useAppTheme';

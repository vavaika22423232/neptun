import { getActiveTheme } from '../../../theme/activeTheme';
import type { ResolvedScheme } from '../../../theme/types';

export type MapGlassTokens = {
  bg: string;
  border: string;
  shadow: string;
  title: string;
  secondary: string;
  accent: string;
  live: string;
};

export function mapGlassTokens(_scheme: ResolvedScheme): MapGlassTokens {
  const c = getActiveTheme().colors;
  const isLight = getActiveTheme().scheme === 'light';
  return {
    bg: isLight ? c.surfaceGlass : c.surfaceGlass,
    border: c.border,
    shadow: isLight ? 'rgba(17, 24, 39, 0.06)' : 'rgba(0, 0, 0, 0.2)',
    title: c.textPrimary,
    secondary: c.textSecondary,
    accent: c.primary,
    live: c.live,
  };
}

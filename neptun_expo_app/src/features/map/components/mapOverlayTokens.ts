import { neptunPalette as p } from '../../../theme/neptunPalette';
import type { ResolvedScheme } from '../../../theme/types';

/** Map floating controls — neutral iOS palette. */
export type MapOverlayTokens = {
  bg: string;
  border: string;
  textPrimary: string;
  textSecondary: string;
  accent: string;
  live: string;
  warning: string;
  pro: string;
};

export function mapOverlayTokens(scheme: ResolvedScheme): MapOverlayTokens {
  const isLight = scheme === 'light';
  return {
    bg: isLight ? p.lightGrouped : p.darkGrouped,
    border: isLight ? p.lightBorder : p.darkBorder,
    textPrimary: isLight ? p.lightTextPrimary : p.darkTextPrimary,
    textSecondary: isLight ? 'rgba(60,60,67,0.72)' : 'rgba(235,235,245,0.72)',
    accent: isLight ? p.link : p.linkDark,
    live: isLight ? p.iosGreen : p.iosGreenDark,
    warning: p.warning,
    pro: isLight ? '#B8860B' : p.proGoldDark,
  };
}

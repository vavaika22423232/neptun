/**
 * Canonical NEPTUN product tokens (8pt grid, iOS settings UI).
 */
import { neptunPalette as p } from '../../theme/neptunPalette';

export const grid = 8;

export const productColors = {
  dark: {
    background: p.darkBackground,
    surface: p.darkGrouped,
    card: p.darkGrouped,
    border: p.darkBorder,
    textPrimary: p.darkTextPrimary,
    textSecondary: 'rgba(235,235,245,0.72)',
    accent: p.linkDark,
    success: p.success,
    warning: p.warning,
    danger: p.danger,
    pro: p.proGoldDark,
  },
  light: {
    background: p.lightBackground,
    surface: p.lightGrouped,
    card: p.lightGrouped,
    border: p.lightBorder,
    textPrimary: p.lightTextPrimary,
    textSecondary: 'rgba(60,60,67,0.72)',
    accent: p.link,
    success: p.success,
    warning: p.warning,
    danger: p.danger,
    pro: '#B8860B',
  },
} as const;

export const productSpacing = {
  screenX: 16,
  screenY: 12,
  cardPadding: 12,
  sectionGap: 16,
  stackGap: 8,
  listItemY: 11,
} as const;

export const productRadius = {
  card: 12,
  sheet: 16,
  button: 10,
  pill: 999,
} as const;

export const productType = {
  display: { size: 32, line: 38, weight: '700' as const },
  screenTitle: { size: 34, line: 40, weight: '700' as const },
  sectionTitle: { size: 13, line: 18, weight: '400' as const },
  cardTitle: { size: 17, line: 22, weight: '600' as const },
  body: { size: 17, line: 22, weight: '400' as const },
  meta: { size: 13, line: 18, weight: '400' as const },
  badge: { size: 11, line: 14, weight: '700' as const },
} as const;

export const elevation = {
  card: { shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0, shadowRadius: 0, elevation: 0 },
  float: { shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0, shadowRadius: 0, elevation: 0 },
} as const;

export { neptunPalette } from '../../theme/neptunPalette';

/**
 * NEPTUN — neutral iOS-style palette (light / dark).
 * Accent colors only on icons & CTAs, not on shell backgrounds.
 */
export const neptunPalette = {
  /** Light */
  lightBackground: '#FFFFFF',
  lightGrouped: '#FFFFFF',
  lightCanvas: '#F2F2F7',
  lightTextPrimary: '#000000',
  lightTextSecondary: '#3C3C43',
  lightTextMuted: '#8E8E93',
  lightBorder: 'rgba(60,60,67,0.18)',
  lightDivider: 'rgba(60,60,67,0.12)',

  /** Dark */
  darkBackground: '#000000',
  darkGrouped: '#1C1C1E',
  darkElevated: '#2C2C2E',
  darkTextPrimary: '#FFFFFF',
  darkTextSecondary: '#EBEBF5',
  darkTextMuted: '#8E8E93',
  darkBorder: 'rgba(255,255,255,0.12)',
  darkDivider: 'rgba(255,255,255,0.10)',

  /** iOS system accents — icon circles & links only */
  iosBlue: '#007AFF',
  iosBlueDark: '#0A84FF',
  iosPurple: '#AF52DE',
  iosPurpleDark: '#BF5AF2',
  iosGreen: '#34C759',
  iosGreenDark: '#30D158',
  iosOrange: '#FF9500',
  iosOrangeDark: '#FF9F0A',
  iosPink: '#FF2D55',
  iosPinkDark: '#FF375F',
  iosRed: '#FF3B30',
  iosRedDark: '#FF453A',
  iosTeal: '#5AC8FA',
  iosTealDark: '#64D2FF',
  iosIndigo: '#5856D6',
  iosIndigoDark: '#5E5CE6',
  iosGray: '#8E8E93',
  iosGrayDark: '#636366',

  /** PRO — muted gold, not teal */
  proGold: '#FFD60A',
  proGoldDark: '#FFD60A',
  proGoldSoft: 'rgba(255,214,10,0.16)',

  /** Actions */
  link: '#007AFF',
  linkDark: '#0A84FF',

  success: '#34C759',
  warning: '#FF9500',
  danger: '#FF3B30',
} as const;

export type NeptunPalette = typeof neptunPalette;

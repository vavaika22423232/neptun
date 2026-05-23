/** Layout & typography tokens — theme-independent. */

export const radii = {
  xs: 4,
  sm: 6,
  md: 8,
  lg: 10,
  xl: 12,
  xxl: 16,
  sheet: 20,
  pill: 999,
} as const;

export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  screenH: 16,
  screenV: 12,
} as const;

export const typography = {
  display: { fontSize: 34, lineHeight: 40, letterSpacing: 0 },
  screenTitle: { fontSize: 27, lineHeight: 33, letterSpacing: 0 },
  sectionTitle: { fontSize: 18, lineHeight: 24 },
  cardTitle: { fontSize: 16, lineHeight: 22 },
  body: { fontSize: 15, lineHeight: 22 },
  bodySmall: { fontSize: 13, lineHeight: 18 },
  caption: { fontSize: 12, lineHeight: 16 },
  badge: { fontSize: 11, lineHeight: 14, letterSpacing: 0.2 },
  /** Legacy aliases */
  title1: { fontSize: 27, lineHeight: 33, letterSpacing: 0 },
  title2: { fontSize: 18, lineHeight: 24 },
  title3: { fontSize: 16, lineHeight: 22 },
  callout: { fontSize: 13, lineHeight: 18 },
  micro: { fontSize: 11, lineHeight: 14, letterSpacing: 0.2 },
} as const;

export const motion = {
  fast: 120,
  normal: 220,
  slow: 360,
  spring: { damping: 18, stiffness: 220 },
} as const;

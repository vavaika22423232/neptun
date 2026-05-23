import { radii, spacing, typography } from './tokens';
import { darkColors } from './darkTheme';
import { lightColors } from './lightTheme';
import type {
  AppTheme,
  ChatThemeTokens,
  LegacyColors,
  LegacyPalette,
  ProfileThemeTokens,
  RadarThemeTokens,
  ResolvedScheme,
  ThemeColors,
  ThemeShadows,
} from './types';

function buildLegacyPalette(c: ThemeColors): LegacyPalette {
  return {
    bg: c.background,
    bgElevated: c.backgroundSecondary,
    bgChrome: c.chrome,
    surface: c.surface,
    surfaceRaised: c.surfaceElevated,
    surfaceGlass: c.surfaceGlass,
    surfaceGlassStrong: c.surfaceGlassStrong,
    surfaceHighlight: c.surfaceHighlight,
    input: c.input,
    overlay: c.overlay,
    scrim: c.scrim,
    border: c.border,
    borderStrong: c.borderStrong,
    divider: c.divider,
    text: c.textPrimary,
    textSoft: c.textSecondary,
    textMuted: c.textMuted,
    textFaint: c.textFaint,
    tabInactive: c.tabInactiveText,
    accent: c.primary,
    accentSoft: c.primary,
    accentMuted: c.primaryMuted,
    success: c.success,
    successMuted: c.successMuted,
    warning: c.warning,
    warningMuted: c.warningMuted,
    danger: c.danger,
    dangerMuted: c.dangerMuted,
    premium: c.pro,
    premiumDeep: c.premiumDeep,
    premiumMuted: c.proSoft,
    mapAlarm: c.mapAlarm,
    mapDrone: c.mapDrone,
    mapMissile: c.mapMissile,
    mapAviation: c.mapAviation,
    mapFire: c.mapFire,
  };
}

function buildLegacyColors(c: ThemeColors): LegacyColors {
  return {
    bg: c.background,
    bg2: c.backgroundSecondary,
    surface: c.surface,
    surface2: c.surfaceElevated,
    surfaceGlass: c.surfaceGlass,
    inputBg: c.input,
    border: c.border,
    borderStrong: c.borderStrong,
    text: c.textPrimary,
    textSoft: c.textSecondary,
    muted: c.textMuted,
    tabInactive: c.tabInactiveText,
    accent: c.primary,
    accent2: c.primary,
    success: c.success,
    warning: c.warning,
    danger: c.danger,
    premium: c.premium,
    mapAlarm: c.mapAlarm,
    mapDrone: c.mapDrone,
    mapMissile: c.mapMissile,
    mapAviation: c.mapAviation,
    mapFire: c.mapFire,
  };
}

function buildShadows(scheme: ResolvedScheme, _c: ThemeColors): ThemeShadows {
  const shadowBase =
    scheme === 'light' ? 'rgba(16, 35, 45, 0.08)' : 'rgba(0, 0, 0, 0.35)';
  const none = {
    shadowColor: 'transparent',
    shadowOpacity: 0,
    shadowRadius: 0,
    shadowOffset: { width: 0, height: 0 },
    elevation: 0,
  };
  return {
    sm: none,
    md: {
      shadowColor: shadowBase,
      shadowOpacity: 1,
      shadowRadius: scheme === 'light' ? 8 : 6,
      shadowOffset: { width: 0, height: 2 },
      elevation: 1,
    },
    sheet: {
      shadowColor: shadowBase,
      shadowOpacity: 1,
      shadowRadius: scheme === 'light' ? 12 : 10,
      shadowOffset: { width: 0, height: -2 },
      elevation: 4,
    },
    glowAccent: none,
  };
}

function buildRadar(c: ThemeColors): RadarThemeTokens {
  return {
    bg: c.cardMuted,
    bgSecondary: c.backgroundSecondary,
    surface: c.card,
    card: c.card,
    border: c.border,
    accent: c.primary,
    accentSoft: c.primarySoft,
    live: c.live,
    warning: c.warning,
    danger: c.danger,
    text: c.textPrimary,
    textSecondary: c.textSecondary,
    textMuted: c.textMuted,
    padH: 16,
    cardPad: 14,
    cardRadius: 18,
    chipRadius: 14,
    cardGap: 12,
    sectionGap: 10,
  };
}

function buildChat(c: ThemeColors, scheme: ResolvedScheme): ChatThemeTokens {
  const isLight = scheme === 'light';
  const chatBg = isLight ? c.cardMuted : '#000000';
  const composerBg = isLight ? '#E9E9EB' : '#1C1C1E';
  return {
    bg: chatBg,
    ambientTop: ['transparent', 'transparent', 'transparent'] as const,
    ambientBottom: ['transparent', chatBg] as const,
    surfaceGlass: composerBg,
    surfaceInput: composerBg,
    border: c.border,
    borderStrong: c.borderStrong,
    divider: c.divider,
    text: c.textPrimary,
    textSoft: c.textSecondary,
    textMuted: c.textMuted,
    textFaint: c.textFaint,
    accent: c.primary,
    accentSoft: c.textPrimary,
    accentMuted: isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.08)',
    onAccent: isLight ? '#FFFFFF' : '#000000',
    premium: c.pro,
    danger: c.danger,
    success: c.success,
    radiusBubble: 18,
    radiusBubbleTail: 18,
    radiusComposer: 26,
    radiusPill: 14,
    radiusGate: 20,
    bubbleMine: isLight ? '#FFFFFF' : '#FFFFFF',
    bubbleOther: isLight ? '#E9E9EB' : '#2C2C2E',
    bubbleSystem: isLight ? c.cardMuted : '#1C1C1E',
    shadowBubble: isLight
      ? {
          shadowColor: 'rgba(0,0,0,0.08)',
          shadowOpacity: 1,
          shadowRadius: 4,
          shadowOffset: { width: 0, height: 1 },
          elevation: 1,
        }
      : {
          shadowColor: 'rgba(0,0,0,0.35)',
          shadowOpacity: 1,
          shadowRadius: 6,
          shadowOffset: { width: 0, height: 2 },
          elevation: 2,
        },
    type: {
      roomTitle: { fontSize: 15, lineHeight: 20, letterSpacing: -0.1 },
      roomSub: { fontSize: 12, lineHeight: 16 },
      message: { fontSize: 15, lineHeight: 20 },
      meta: { fontSize: 10, lineHeight: 13, letterSpacing: 0.1 },
      composer: { fontSize: 15, lineHeight: 20 },
      filter: { fontSize: 13, lineHeight: 18 },
    },
  };
}

function buildProfile(c: ThemeColors, scheme: ResolvedScheme): ProfileThemeTokens {
  const isLight = scheme === 'light';
  return {
    screenBg: c.background,
    ambientTop: isLight
      ? (['transparent', 'transparent'] as const)
      : (['transparent', 'transparent'] as const),
    cardBg: c.card,
    cardBgElevated: c.cardElevated,
    cardBorder: c.border,
    cardShadow: 'transparent',
    heroGradient: isLight
      ? ([c.card, c.card] as const)
      : ([c.card, c.card] as const),
    heroRing: c.border,
    premiumGradient: isLight
      ? ([c.proSoft, c.proSoft, c.proSoft] as const)
      : ([c.proSoft, c.proSoft, c.proSoft] as const),
    premiumGradientSoft: isLight
      ? ([c.proSoft, c.proSoft] as const)
      : ([c.proSoft, c.proSoft] as const),
    premiumAccent: c.pro,
    premiumGlow: c.proSoft,
    freeBg: c.surfaceHighlight,
    freeText: c.textMuted,
    statusCalm: c.success,
    iconBg: c.surfaceHighlight,
    divider: c.divider,
    sectionLabel: c.textFaint,
    textPrimary: c.textPrimary,
    textSecondary: c.textMuted,
    textTertiary: c.textFaint,
    radiusCard: radii.xl,
    radiusRow: radii.lg,
    radiusAvatar: 22,
    avatarSize: 68,
    insetH: spacing.screenH,
    sectionGap: 26,
    rowPadV: 14,
    groupGap: 10,
  };
}

export function createAppTheme(scheme: ResolvedScheme): AppTheme {
  const colors = scheme === 'light' ? lightColors : darkColors;
  const palette = buildLegacyPalette(colors);
  return {
    scheme,
    colors,
    palette,
    legacyColors: buildLegacyColors(colors),
    radar: buildRadar(colors),
    chat: buildChat(colors, scheme),
    profile: buildProfile(colors, scheme),
    shadows: buildShadows(scheme, colors),
    glass: {
      card: {
        backgroundColor: colors.surfaceGlass,
        borderWidth: 1,
        borderColor: colors.border,
      },
      chrome: {
        backgroundColor: colors.chrome,
        borderBottomColor: colors.border,
      },
    },
    radii,
    spacing,
    typography,
  };
}

export const darkAppTheme = createAppTheme('dark');
export const lightAppTheme = createAppTheme('light');

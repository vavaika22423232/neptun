import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo, useEffect, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { relativeTimeUk } from '../../map/utils/relativeTimeUk';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import type { ConnectionStatus } from '../types/radar.types';
import type { ResolvedScheme } from '../../../theme/types';
import { neptunPalette as p } from '../../../theme/neptunPalette';

export type RadarTopPanelConnection = 'online' | 'connecting' | 'offline';

export type RadarTopPanelProps = {
  liveCount?: number;
  isLive?: boolean;
  lastUpdatedAt?: string | Date | number | null;
  connectionStatus?: RadarTopPanelConnection | ConnectionStatus;
  isPremium?: boolean;
  showModeratorAction?: boolean;
  onBrandPress?: () => void;
  onTelegramPress?: () => void;
  onSafetyPress?: () => void;
  onProPress?: () => void;
  onThemePress?: () => void;
  onModeratorPress?: () => void;
};

type PanelTokens = {
  shellBg: string;
  panelBg: string;
  cardBg: string;
  border: string;
  title: string;
  secondary: string;
  muted: string;
  accent: string;
  live: string;
  liveGlow: string;
  warning: string;
  premium: string;
  premiumBg: string;
  premiumBorder: string;
  iconBtnBg: string;
  shadow: string;
  chipBg: string;
  verifiedBg: string;
};

function panelTokens(scheme: ResolvedScheme): PanelTokens {
  if (scheme === 'light') {
    return {
      shellBg: p.lightBackground,
      panelBg: 'rgba(255,255,255,0.96)',
      cardBg: p.lightGrouped,
      border: p.lightBorder,
      title: p.lightTextPrimary,
      secondary: 'rgba(60,60,67,0.72)',
      muted: p.lightTextMuted,
      accent: p.link,
      live: p.iosGreen,
      liveGlow: 'rgba(52,199,89,0.18)',
      warning: p.warning,
      premium: '#B8860B',
      premiumBg: 'rgba(255,204,0,0.14)',
      premiumBorder: 'rgba(255,204,0,0.28)',
      iconBtnBg: p.lightCanvas,
      shadow: 'rgba(0,0,0,0.06)',
      chipBg: p.lightCanvas,
      verifiedBg: 'rgba(0,122,255,0.10)',
    };
  }
  return {
    shellBg: p.darkBackground,
    panelBg: 'rgba(28,28,30,0.96)',
    cardBg: p.darkGrouped,
    border: p.darkBorder,
    title: p.darkTextPrimary,
    secondary: 'rgba(235,235,245,0.72)',
    muted: p.darkTextMuted,
    accent: p.linkDark,
    live: p.iosGreenDark,
    liveGlow: 'rgba(48,209,88,0.18)',
    warning: p.warning,
    premium: p.proGoldDark,
    premiumBg: 'rgba(255,214,10,0.12)',
    premiumBorder: 'rgba(255,214,10,0.24)',
    iconBtnBg: p.darkElevated,
    shadow: 'rgba(0,0,0,0.40)',
    chipBg: p.darkElevated,
    verifiedBg: 'rgba(10,132,255,0.14)',
  };
}

function normalizeConnection(
  status?: RadarTopPanelConnection | ConnectionStatus,
): RadarTopPanelConnection {
  if (status === 'live' || status === 'online') return 'online';
  if (status === 'connecting' || status === 'stale') return 'connecting';
  return 'offline';
}

function connectionLabel(status: RadarTopPanelConnection): string {
  switch (status) {
    case 'online':
      return 'Онлайн';
    case 'connecting':
      return 'Зʼєднання…';
    default:
      return 'Офлайн';
  }
}

function radarSubtitle(status: RadarTopPanelConnection, isLive: boolean): string {
  if (status === 'connecting') return 'Підключення до каналу…';
  if (status === 'offline') return 'Очікуємо зʼєднання';
  return isLive ? 'Моніторинг активний' : 'Готово до моніторингу';
}

function formatCount(n: number): string {
  return n.toLocaleString('uk-UA');
}

function parseUpdatedAt(raw?: string | Date | number | null): Date | null {
  if (raw == null) return null;
  if (typeof raw === 'number') return new Date(raw);
  if (raw instanceof Date) return raw;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

const LivePulseDot = memo(function LivePulseDot({ color, glow, active }: { color: string; glow: string; active: boolean }) {
  const pulse = useSharedValue(1);
  useEffect(() => {
    if (!active) return;
    pulse.value = withRepeat(
      withSequence(
        withTiming(1.4, { duration: 900, easing: Easing.inOut(Easing.ease) }),
        withTiming(1, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      false,
    );
  }, [active, pulse]);
  const ring = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
    opacity: active ? 0.4 : 0,
  }));
  return (
    <View style={dotStyles.wrap}>
      {active ? <Animated.View style={[dotStyles.ring, { backgroundColor: glow }, ring]} /> : null}
      <View style={[dotStyles.core, { backgroundColor: active ? color : glow }]} />
    </View>
  );
});

const dotStyles = StyleSheet.create({
  wrap: { width: 12, height: 12, alignItems: 'center', justifyContent: 'center' },
  ring: { position: 'absolute', width: 12, height: 12, borderRadius: 6 },
  core: { width: 8, height: 8, borderRadius: 4 },
});

const PanelIconButton = memo(function PanelIconButton({
  icon,
  color,
  tokens,
  onPress,
  accessibilityLabel,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  color: string;
  tokens: PanelTokens;
  onPress?: () => void;
  accessibilityLabel?: string;
}) {
  return (
    <NeptunPressable
      haptic
      scaleTo={0.94}
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      style={[
        iconBtnStyles.btn,
        { backgroundColor: tokens.iconBtnBg, borderColor: tokens.border },
      ]}
    >
      <Ionicons name={icon} size={20} color={color} />
    </NeptunPressable>
  );
});

const iconBtnStyles = StyleSheet.create({
  btn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: StyleSheet.hairlineWidth,
  },
});

const QuickActionChip = memo(function QuickActionChip({
  icon,
  label,
  color,
  tokens,
  highlight,
  onPress,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  color: string;
  tokens: PanelTokens;
  highlight?: boolean;
  onPress?: () => void;
}) {
  return (
    <NeptunPressable
      haptic
      scaleTo={0.97}
      onPress={onPress}
      style={[
        chipStyles.chip,
        {
          backgroundColor: highlight ? tokens.premiumBg : tokens.chipBg,
          borderColor: highlight ? tokens.premiumBorder : tokens.border,
        },
      ]}
    >
      <Ionicons name={icon} size={17} color={color} />
      <Text style={[chipStyles.label, { color: highlight ? tokens.premium : tokens.title }]} numberOfLines={1}>
        {label}
      </Text>
    </NeptunPressable>
  );
});

const chipStyles = StyleSheet.create({
  chip: {
    flex: 1,
    minWidth: 0,
    height: 40,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 10,
    borderWidth: StyleSheet.hairlineWidth,
  },
  label: {
    fontFamily: fonts.semiBold,
    fontSize: 13,
  },
});

function RadarTopPanelInner({
  liveCount = 0,
  isLive = false,
  lastUpdatedAt = null,
  connectionStatus = 'connecting',
  isPremium = false,
  showModeratorAction = false,
  onBrandPress,
  onTelegramPress,
  onSafetyPress,
  onProPress,
  onThemePress,
  onModeratorPress,
}: RadarTopPanelProps) {
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const tokens = useMemo(() => panelTokens(theme.scheme), [theme.scheme]);
  const styles = useRadarTopPanelStyles();

  const conn = normalizeConnection(connectionStatus);
  const updatedAt = parseUpdatedAt(lastUpdatedAt);
  const lastUpdateLabel = updatedAt ? `оновлено ${relativeTimeUk(updatedAt)}` : 'оновлення очікується';
  const showPulse = conn === 'online' && (isLive || liveCount > 0);
  const themeIcon: ComponentProps<typeof Ionicons>['name'] =
    theme.scheme === 'dark' ? 'sunny-outline' : 'moon-outline';
  const safetyHandler = showModeratorAction ? onModeratorPress : onSafetyPress;

  const counterOpacity = useSharedValue(1);
  useEffect(() => {
    counterOpacity.value = withSequence(
      withTiming(0.5, { duration: 100 }),
      withTiming(1, { duration: 220 }),
    );
  }, [liveCount, counterOpacity]);
  const counterAnim = useAnimatedStyle(() => ({ opacity: counterOpacity.value }));

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 10, backgroundColor: tokens.shellBg }]}>
      <View
        style={[
          styles.panel,
          {
            backgroundColor: tokens.panelBg,
            borderColor: tokens.border,
            shadowColor: tokens.shadow,
          },
        ]}
      >
        {/* Brand row */}
        <View style={styles.brandRow}>
          <NeptunPressable haptic={false} scaleTo={0.99} style={styles.brandLeft} onPress={onBrandPress}>
            <View style={styles.brandTitleRow}>
              <View style={[styles.brandIcon, { backgroundColor: tokens.verifiedBg }]}>
                <Ionicons name="radio" size={18} color={tokens.accent} />
              </View>
              <View style={styles.brandTextCol}>
                <Text style={[styles.appTitle, { color: tokens.title }]}>Dron Alerts</Text>
                <Text style={[styles.appSubtitle, { color: tokens.secondary }]}>
                  Система моніторингу в реальному часі
                </Text>
              </View>
            </View>
          </NeptunPressable>
          <View style={styles.brandActions}>
            <PanelIconButton
              icon="paper-plane-outline"
              color={tokens.accent}
              tokens={tokens}
              accessibilityLabel="Telegram"
              onPress={onTelegramPress}
            />
            <PanelIconButton
              icon={showModeratorAction ? 'shield-checkmark' : 'shield-outline'}
              color={showModeratorAction ? tokens.warning : tokens.secondary}
              tokens={tokens}
              accessibilityLabel={showModeratorAction ? 'Модератор' : 'Безпека'}
              onPress={safetyHandler}
            />
            <NeptunPressable
              haptic
              scaleTo={0.94}
              onPress={onProPress}
              style={[
                styles.proPill,
                {
                  backgroundColor: tokens.premiumBg,
                  borderColor: tokens.premiumBorder,
                },
              ]}
            >
              <Ionicons name={isPremium ? 'star' : 'ribbon-outline'} size={16} color={tokens.premium} />
              <Text style={[styles.proLabel, { color: tokens.premium }]}>PRO</Text>
            </NeptunPressable>
            <PanelIconButton
              icon={themeIcon}
              color={tokens.secondary}
              tokens={tokens}
              accessibilityLabel="Тема"
              onPress={onThemePress}
            />
          </View>
        </View>

        {/* Radar status mini-dashboard */}
        <View
          style={[
            styles.statusCard,
            { backgroundColor: tokens.cardBg, borderColor: tokens.border },
          ]}
        >
          <View style={styles.statusLeft}>
            <Text style={[styles.radarTitle, { color: tokens.title }]}>Радар</Text>
            <Text style={[styles.radarSubtitle, { color: tokens.secondary }]}>
              {radarSubtitle(conn, isLive)}
            </Text>
            <View style={styles.connRow}>
              <LivePulseDot color={tokens.live} glow={tokens.liveGlow} active={showPulse} />
              <Text
                style={[
                  styles.connLabel,
                  {
                    color:
                      conn === 'online' ? tokens.live : conn === 'connecting' ? tokens.warning : tokens.muted,
                  },
                ]}
              >
                {connectionLabel(conn)}
              </Text>
              <View style={[styles.connDot, { backgroundColor: tokens.border }]} />
              <Text style={[styles.lastUpdate, { color: tokens.muted }]} numberOfLines={1}>
                {lastUpdateLabel}
              </Text>
            </View>
          </View>
          <View style={styles.statusRight}>
            <View style={[styles.liveBadge, { backgroundColor: tokens.liveGlow, borderColor: tokens.border }]}>
              <Text style={[styles.liveBadgeText, { color: tokens.live }]}>LIVE</Text>
            </View>
            <Animated.Text style={[styles.counter, { color: tokens.title }, counterAnim]}>
              {formatCount(liveCount)}
            </Animated.Text>
            <Text style={[styles.counterHint, { color: tokens.secondary }]}>онлайн</Text>
          </View>
        </View>

        {/* Quick actions */}
        <View style={styles.quickRow}>
          <QuickActionChip
            icon="paper-plane"
            label="Telegram"
            color={tokens.accent}
            tokens={tokens}
            onPress={onTelegramPress}
          />
          <QuickActionChip
            icon={showModeratorAction ? 'shield-checkmark' : 'shield-outline'}
            label={showModeratorAction ? 'Модератор' : 'Безпека'}
            color={showModeratorAction ? tokens.warning : tokens.secondary}
            tokens={tokens}
            onPress={safetyHandler}
          />
          <QuickActionChip
            icon={isPremium ? 'star' : 'ribbon-outline'}
            label="PRO"
            color={tokens.premium}
            tokens={tokens}
            highlight
            onPress={onProPress}
          />
          <QuickActionChip
            icon={themeIcon}
            label="Тема"
            color={tokens.secondary}
            tokens={tokens}
            onPress={onThemePress}
          />
        </View>

        <View style={[styles.divider, { backgroundColor: tokens.border }]} />

        {/* Official Telegram card */}
        <NeptunPressable haptic scaleTo={0.99} style={styles.telegramCard} onPress={onTelegramPress}>
          <View style={[styles.telegramIcon, { backgroundColor: tokens.verifiedBg, borderColor: tokens.border }]}>
            <Ionicons name="paper-plane" size={20} color={tokens.accent} />
          </View>
          <View style={styles.telegramBody}>
            <View style={styles.telegramTitleRow}>
              <Text style={[styles.telegramTitle, { color: tokens.title }]} numberOfLines={1}>
                Офіційний Telegram канал
              </Text>
              <View style={[styles.verifiedBadge, { backgroundColor: tokens.verifiedBg }]}>
                <Ionicons name="checkmark-circle" size={14} color={tokens.accent} />
              </View>
            </View>
            <Text style={[styles.telegramSub, { color: tokens.secondary }]} numberOfLines={2}>
              Швидкі оновлення та важливі повідомлення
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={tokens.muted} />
        </NeptunPressable>
      </View>
    </View>
  );
}

function useRadarTopPanelStyles() {
  return useThemedStyles(() =>
    StyleSheet.create({
      shell: { width: '100%' },
      panel: {
        marginHorizontal: 0,
        paddingHorizontal: 20,
        paddingTop: 14,
        paddingBottom: 18,
        borderBottomLeftRadius: 32,
        borderBottomRightRadius: 32,
        borderWidth: StyleSheet.hairlineWidth,
        shadowOffset: { width: 0, height: 12 },
        shadowOpacity: 1,
        shadowRadius: 28,
        elevation: 10,
        gap: 12,
      },
      brandRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
      },
      brandLeft: { flex: 1, minWidth: 0 },
      brandTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
      brandIcon: {
        width: 40,
        height: 40,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
      },
      brandTextCol: { flex: 1, minWidth: 0, gap: 2 },
      appTitle: {
        fontFamily: fonts.bold,
        fontSize: 28,
        letterSpacing: -0.5,
        lineHeight: 32,
      },
      appSubtitle: {
        fontFamily: fonts.medium,
        fontSize: 13,
        lineHeight: 18,
      },
      brandActions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        flexShrink: 0,
        paddingTop: 2,
      },
      proPill: {
        height: 44,
        paddingHorizontal: 11,
        borderRadius: 22,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        borderWidth: StyleSheet.hairlineWidth,
      },
      proLabel: {
        fontFamily: fonts.bold,
        fontSize: 12,
        letterSpacing: 0.3,
      },
      statusCard: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        padding: 14,
        borderRadius: 22,
        borderWidth: StyleSheet.hairlineWidth,
      },
      statusLeft: { flex: 1, minWidth: 0, gap: 4 },
      radarTitle: {
        fontFamily: fonts.bold,
        fontSize: 21,
        letterSpacing: -0.3,
      },
      radarSubtitle: {
        fontFamily: fonts.medium,
        fontSize: 14,
      },
      connRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginTop: 6,
        flexWrap: 'wrap',
      },
      connLabel: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
      },
      connDot: {
        width: 4,
        height: 4,
        borderRadius: 2,
      },
      lastUpdate: {
        fontFamily: fonts.medium,
        fontSize: 12,
        flexShrink: 1,
      },
      statusRight: {
        alignItems: 'flex-end',
        gap: 2,
        minWidth: 88,
      },
      liveBadge: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 8,
        borderWidth: StyleSheet.hairlineWidth,
        marginBottom: 2,
      },
      liveBadgeText: {
        fontFamily: fonts.bold,
        fontSize: 10,
        letterSpacing: 0.8,
      },
      counter: {
        fontFamily: fonts.bold,
        fontSize: 26,
        letterSpacing: -0.5,
        lineHeight: 30,
      },
      counterHint: {
        fontFamily: fonts.medium,
        fontSize: 12,
      },
      quickRow: {
        flexDirection: 'row',
        gap: 8,
      },
      divider: {
        height: StyleSheet.hairlineWidth,
        opacity: 0.85,
      },
      telegramCard: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 4,
        minHeight: 56,
      },
      telegramIcon: {
        width: 46,
        height: 46,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: StyleSheet.hairlineWidth,
      },
      telegramBody: { flex: 1, minWidth: 0, gap: 3 },
      telegramTitleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
      },
      telegramTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 15,
        flexShrink: 1,
      },
      verifiedBadge: {
        width: 22,
        height: 22,
        borderRadius: 11,
        alignItems: 'center',
        justifyContent: 'center',
      },
      telegramSub: {
        fontFamily: fonts.medium,
        fontSize: 12,
        lineHeight: 17,
      },
    }),
  );
}

export const RadarTopPanel = memo(RadarTopPanelInner);

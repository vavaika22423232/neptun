import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { HeaderIconButton } from '../../../components/ui/HeaderIconButton';
import { ProEntryPill } from '../../pro/components/ProEntryPill';
import { HeaderLiveIndicator } from '../../../components/ui/HeaderLiveIndicator';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { relativeTimeUk } from '../../map/utils/relativeTimeUk';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import type { ResolvedScheme } from '../../../theme/types';
import { neptunPalette as p } from '../../../theme/neptunPalette';
export type RadarHeaderConnection = 'online' | 'connecting' | 'offline';

export type RadarHeaderDashboardProps = {
  liveCount?: number;
  isLive?: boolean;
  lastUpdatedAt?: string | Date | number | null;
  connectionStatus?: RadarHeaderConnection;
  isPremium?: boolean;
  showModeratorAction?: boolean;
  onBrandPress?: () => void;
  onTelegramPress?: () => void;
  onSafetyPress?: () => void;
  onProPress?: () => void;
  onThemePress?: () => void;
  onModeratorPress?: () => void;
  onSearchPress?: () => void;
};

function panelTokens(scheme: ResolvedScheme) {
  if (scheme === 'light') {
    return {
      shell: p.lightBackground,
      panel: 'rgba(255,255,255,0.96)',
      border: p.lightBorder,
      shadow: 'rgba(0,0,0,0.06)',
    };
  }
  return {
    shell: p.darkBackground,
    panel: 'rgba(28,28,30,0.96)',
    border: p.darkBorder,
    shadow: 'rgba(0,0,0,0.40)',
  };
}

function parseUpdatedAt(raw?: string | Date | number | null): Date | null {
  if (raw == null) return null;
  if (typeof raw === 'number') return new Date(raw);
  if (raw instanceof Date) return raw;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

function connLabel(status: RadarHeaderConnection): string {
  if (status === 'online') return 'Онлайн';
  if (status === 'connecting') return 'Зʼєднання…';
  return 'Офлайн';
}

/** Compact live dashboard header for Radar tab only. */
function RadarHeaderDashboardInner({
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
  onSearchPress,
}: RadarHeaderDashboardProps) {
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const tok = useMemo(() => panelTokens(theme.scheme), [theme.scheme]);
  const styles = useRadarHeaderStyles();
  const updated = parseUpdatedAt(lastUpdatedAt);
  const updateLabel = updated ? relativeTimeUk(updated) : 'очікується';
  const safetyHandler = showModeratorAction ? onModeratorPress : onSafetyPress;
  const themeIcon: ComponentProps<typeof Ionicons>['name'] =
    theme.scheme === 'dark' ? 'sunny-outline' : 'moon-outline';

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 8, backgroundColor: tok.shell }]}>
      <View
        style={[
          styles.panel,
          {
            backgroundColor: tok.panel,
            borderColor: tok.border,
            shadowColor: tok.shadow,
          },
        ]}
      >
        <View style={styles.mainRow}>
          <NeptunPressable haptic={false} style={styles.titleCol} onPress={onBrandPress}>
            <View style={styles.titleRow}>
              <Text style={styles.title}>Радар</Text>
              {isLive ? <HeaderLiveIndicator active size="sm" /> : null}
            </View>
            <Text style={styles.subtitle} numberOfLines={1}>
              {connectionStatus === 'online' ? 'Моніторинг активний' : connLabel(connectionStatus)}
              {liveCount > 0 ? ` · ${liveCount.toLocaleString('uk-UA')} онлайн` : ''}
            </Text>
          </NeptunPressable>
          <View style={styles.actions}>
            {onSearchPress ? (
              <HeaderIconButton icon="search-outline" accessibilityLabel="Пошук" onPress={onSearchPress} />
            ) : null}
            <HeaderIconButton
              icon="paper-plane-outline"
              tone="accent"
              accessibilityLabel="Telegram"
              onPress={onTelegramPress}
            />
            <HeaderIconButton
              icon={showModeratorAction ? 'shield-checkmark' : 'shield-outline'}
              tone={showModeratorAction ? 'warning' : 'default'}
              accessibilityLabel={showModeratorAction ? 'Модератор' : 'Безпека'}
              onPress={safetyHandler}
            />
            {isPremium ? null : onProPress ? (
              <ProEntryPill compact onPress={onProPress} />
            ) : null}
            <HeaderIconButton icon={themeIcon} accessibilityLabel="Тема" onPress={onThemePress} />
          </View>
        </View>

        <View style={styles.footerRow}>
          <View style={styles.metaPill}>
            <Text style={styles.metaText}>оновлено {updateLabel}</Text>
          </View>
          <NeptunPressable haptic scaleTo={0.98} style={styles.tgPill} onPress={onTelegramPress}>
            <Ionicons name="paper-plane" size={14} color={theme.colors.primary} />
            <Text style={styles.tgText}>Telegram</Text>
            <Ionicons name="chevron-forward" size={14} color={theme.colors.textMuted} />
          </NeptunPressable>
        </View>
      </View>
    </View>
  );
}

function useRadarHeaderStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: { width: '100%' },
      panel: {
        paddingHorizontal: 18,
        paddingTop: 12,
        paddingBottom: 12,
        borderBottomLeftRadius: 26,
        borderBottomRightRadius: 26,
        borderWidth: StyleSheet.hairlineWidth,
        gap: 10,
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 1,
        shadowRadius: 18,
        elevation: 6,
      },
      mainRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
      },
      titleCol: { flex: 1, minWidth: 0, gap: 2 },
      titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
      title: {
        fontFamily: fonts.bold,
        fontSize: 24,
        color: t.colors.textPrimary,
        letterSpacing: -0.3,
      },
      subtitle: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
      actions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        flexShrink: 0,
      },
      footerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
      },
      metaPill: {
        flex: 1,
        paddingHorizontal: 10,
        paddingVertical: 7,
        borderRadius: 14,
        backgroundColor: t.colors.surfaceHighlight,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      metaText: {
        fontFamily: fonts.medium,
        fontSize: 12,
        color: t.colors.textMuted,
      },
      tgPill: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 10,
        paddingVertical: 7,
        borderRadius: 14,
        backgroundColor: t.colors.primaryMuted,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      tgText: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
        color: t.colors.primary,
      },
    }),
  );
}

export const RadarHeaderDashboard = memo(RadarHeaderDashboardInner);

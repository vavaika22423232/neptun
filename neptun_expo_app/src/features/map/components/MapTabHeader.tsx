import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { HeaderLiveIndicator } from '../../../components/ui/HeaderLiveIndicator';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { relativeTimeUk } from '../utils/relativeTimeUk';
import { useMapStore } from '../state/mapStore';
import { MapPlaceSearchPanel } from './MapPlaceSearchPanel';
import { MapTelegramBanner } from './MapTelegramBanner';

/** Visible bar height (title + action row), excluding safe area. */
export const MAP_TAB_HEADER_HEIGHT = 114;

export type MapTabHeaderProps = {
  onStatusPress?: () => void;
  onRegionsPress?: () => void;
  onProPress?: () => void;
  onTelegramPress?: () => void;
  isPaid?: boolean;
};

function compactTime(linkPhase: string, lastRefresh?: number): string {
  switch (linkPhase) {
    case 'live':
      if (!lastRefresh) return 'щойно';
      return relativeTimeUk(new Date(lastRefresh));
    case 'connecting':
      return 'зʼєднання…';
    case 'reconnecting':
    case 'offline':
      return 'офлайн';
    default:
      return '…';
  }
}

/** Normal fixed top app bar over the live map. */
function MapTabHeaderInner({
  onStatusPress,
  onRegionsPress,
  onProPress,
  onTelegramPress,
  isPaid,
}: MapTabHeaderProps) {
  const insets = useSafeAreaInsets();
  const { theme, setMode } = useAppTheme();
  const styles = useHeaderStyles();
  const [searchOpen, setSearchOpen] = useState(false);

  const linkPhase = useMapStore((s) => s.linkPhase);
  const lastRefresh = useMapStore((s) => s.lastSignificantRefreshAt);
  const alarms = useMapStore((s) => s.alarms);
  const markers = useMapStore((s) => s.markers);

  const isLive = linkPhase === 'live';
  const regions = alarms.stateCount ?? 0;
  const events = markers.length;

  const statusLine = useMemo(() => {
    const time = compactTime(linkPhase, lastRefresh);
    if (regions > 0) {
      const word = regions === 1 ? 'тривога' : regions < 5 ? 'тривоги' : 'тривог';
      return `${regions} ${word} · ${time}`;
    }
    if (events > 0) {
      const word = events === 1 ? 'подія' : 'подій';
      return `${events} ${word} · ${time}`;
    }
    return `Спокійно · ${time}`;
  }, [regions, events, linkPhase, lastRefresh]);

  const statusColor =
    regions > 0 ? theme.colors.warning : events > 0 ? theme.colors.primary : theme.colors.textMuted;

  const toggleTheme = () => {
    setMode(theme.scheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <View
      style={[styles.shell, { paddingTop: insets.top }]}
      pointerEvents="box-none"
    >
      <View style={styles.bar}>
        <View style={styles.topRow}>
          <NeptunPressable
            haptic={false}
            style={styles.leading}
            onPress={onStatusPress}
            disabled={!onStatusPress}
          >
            <Text style={styles.title}>Карта</Text>
            <View style={styles.statusRow}>
              <HeaderLiveIndicator active={isLive} size="sm" />
              <Text style={[styles.status, { color: statusColor }]} numberOfLines={1}>
                {statusLine}
              </Text>
            </View>
          </NeptunPressable>

          <View style={styles.primaryActions}>
            <NeptunPressable
              haptic
              accessibilityLabel="Регіони"
              onPress={onRegionsPress}
              style={styles.regionsButton}
            >
              <Ionicons name="notifications-outline" size={14} color={styles.regionsColor.color} />
              <Text style={styles.regionsText}>Регіони</Text>
            </NeptunPressable>
            <NeptunPressable
              haptic
              accessibilityLabel={isPaid ? 'PRO Версія активна' : 'Відкрити PRO Версія'}
              onPress={onProPress}
              style={[styles.proButton, isPaid && styles.proButtonActive]}
            >
              <Ionicons name="sparkles" size={14} color={isPaid ? styles.proActiveColor.color : styles.proColor.color} />
              <Text style={[styles.proText, isPaid && styles.proTextActive]}>PRO Версія</Text>
            </NeptunPressable>
            <HeaderIcon
              icon={theme.scheme === 'dark' ? 'sunny-outline' : 'moon-outline'}
              label="Перемкнути тему"
              onPress={toggleTheme}
              styles={styles}
            />
          </View>
        </View>

        {!searchOpen ? (
          <View style={styles.actionRow}>
            <NeptunPressable
              haptic
              accessibilityLabel="Пошук міста або населеного пункту"
              onPress={() => setSearchOpen(true)}
              style={styles.searchSegment}
            >
              <Ionicons name="search-outline" size={16} color={styles.searchIconColor.color} />
              <Text style={styles.searchText} numberOfLines={1}>
                Пошук місця…
              </Text>
            </NeptunPressable>
            <MapTelegramBanner compact onPress={onTelegramPress} />
          </View>
        ) : null}

        <MapPlaceSearchPanel open={searchOpen} onClose={() => setSearchOpen(false)} />
      </View>
    </View>
  );
}

function HeaderIcon({
  icon,
  label,
  onPress,
  styles,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  onPress?: () => void;
  styles: ReturnType<typeof useHeaderStyles>;
}) {
  return (
    <NeptunPressable haptic accessibilityLabel={label} onPress={onPress} style={styles.iconBtn}>
      <Ionicons name={icon} size={18} color={styles.iconColor.color} />
    </NeptunPressable>
  );
}

function useHeaderStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      shell: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 25,
        elevation: 25,
        backgroundColor: t.colors.chrome,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.border,
      },
      bar: {
        minHeight: MAP_TAB_HEADER_HEIGHT,
        paddingHorizontal: 14,
        paddingTop: 6,
        paddingBottom: 8,
        gap: 8,
      },
      topRow: {
        minHeight: 42,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
      },
      leading: {
        flex: 1,
        minWidth: 0,
        justifyContent: 'center',
        gap: 2,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 17,
        letterSpacing: -0.2,
        color: t.colors.textPrimary,
      },
      statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
      },
      status: {
        flexShrink: 1,
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
      },
      primaryActions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        flexShrink: 0,
      },
      actionRow: {
        height: 40,
        flexDirection: 'row',
        alignItems: 'stretch',
        borderRadius: 14,
        overflow: 'hidden',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.input,
      },
      searchSegment: {
        flex: 1,
        minWidth: 0,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 12,
      },
      searchText: {
        flex: 1,
        minWidth: 0,
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textMuted,
      },
      iconBtn: {
        width: 38,
        height: 38,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceHighlight,
      },
      proButton: {
        height: 34,
        borderRadius: 14,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 10,
        backgroundColor: t.colors.proSoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: isDark ? 'rgba(255,214,10,0.28)' : 'rgba(184,134,11,0.22)',
      },
      regionsButton: {
        height: 34,
        borderRadius: 14,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 10,
        backgroundColor: t.colors.primaryMuted,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: isDark ? 'rgba(74,141,255,0.28)' : 'rgba(37,99,235,0.18)',
      },
      regionsText: {
        fontFamily: fonts.bold,
        fontSize: 12,
        color: t.colors.primary,
      },
      proButtonActive: {
        backgroundColor: t.colors.pro,
      },
      proText: {
        fontFamily: fonts.bold,
        fontSize: 12,
        color: t.colors.pro,
      },
      proTextActive: {
        color: t.colors.textInverse,
      },
      iconColor: { color: t.colors.textPrimary },
      regionsColor: { color: t.colors.primary },
      proColor: { color: t.colors.pro },
      proActiveColor: { color: t.colors.textInverse },
      searchIconColor: { color: t.colors.textMuted },
    });
  });
}

/** Y-offset for banners below the fixed map header. */
export function mapTabHeaderBottom(safeTop: number): number {
  return safeTop + MAP_TAB_HEADER_HEIGHT + 10;
}

export const MapTabHeader = memo(MapTabHeaderInner);

/** @deprecated Use mapTabHeaderBottom */
export function mapNavBarHeight(safeTop: number): number {
  return mapTabHeaderBottom(safeTop);
}

export const MAP_NAV_CONTENT_HEIGHT = MAP_TAB_HEADER_HEIGHT;

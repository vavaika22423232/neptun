import { memo, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useAppTheme } from '../../../theme/useAppTheme';
import { relativeTimeUk } from '../utils/relativeTimeUk';
import { useMapStore } from '../state/mapStore';
import { mapOverlayTokens } from './mapOverlayTokens';

export type MapMiniStatusChipProps = {
  updatedLabel?: string;
  isLive?: boolean;
};

function compactLabel(linkPhase: string, lastRefresh?: number): string {
  switch (linkPhase) {
    case 'live':
      if (!lastRefresh) return 'щойно';
      return relativeTimeUk(new Date(lastRefresh)).replace(/\s+тому$/, '');
    case 'connecting':
      return 'зʼєднання';
    case 'reconnecting':
    case 'offline':
      return 'офлайн';
    default:
      return '…';
  }
}

function MapMiniStatusChipInner({ updatedLabel, isLive: isLiveProp }: MapMiniStatusChipProps) {
  const { theme } = useAppTheme();
  const tokens = useMemo(() => mapOverlayTokens(theme.scheme), [theme.scheme]);
  const linkPhase = useMapStore((s) => s.linkPhase);
  const lastRefresh = useMapStore((s) => s.lastSignificantRefreshAt);

  const isLive = isLiveProp ?? linkPhase === 'live';
  const status = updatedLabel ?? compactLabel(linkPhase, lastRefresh);

  return (
    <View
      style={[
        styles.chip,
        { backgroundColor: tokens.bg, borderColor: tokens.border },
      ]}
    >
      <Text style={[styles.title, { color: tokens.textPrimary }]}>Live</Text>
      <View style={[styles.dot, { backgroundColor: isLive ? tokens.live : tokens.textSecondary }]} />
      <Text style={[styles.status, { color: tokens.textSecondary }]} numberOfLines={1}>
        {status}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 42,
    maxWidth: 160,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 6,
  },
  title: {
    fontFamily: fonts.semiBold,
    fontSize: 15,
    letterSpacing: -0.2,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  status: {
    flexShrink: 1,
    fontFamily: fonts.medium,
    fontSize: 12,
  },
});

export const MapMiniStatusChip = memo(MapMiniStatusChipInner);

import { memo, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../../../components/ui/AppText';
import { HeaderLiveIndicator } from '../../../components/ui/HeaderLiveIndicator';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { relativeTimeUk } from '../../map/utils/relativeTimeUk';

type Props = {
  eventCount: number;
  highAttentionCount?: number;
  connectionStatus: 'online' | 'connecting' | 'offline';
  lastUpdatedAt?: string | Date | number | null;
  onlineCount?: number;
};

function parseUpdatedAt(raw?: string | Date | number | null): Date | null {
  if (raw == null) return null;
  if (typeof raw === 'number') return new Date(raw);
  if (raw instanceof Date) return raw;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

function RadarStatusSummaryInner({
  eventCount,
  highAttentionCount = 0,
  connectionStatus,
  lastUpdatedAt,
  onlineCount = 0,
}: Props) {
  const { theme } = useAppTheme();
  const styles = useSummaryStyles();
  const updated = parseUpdatedAt(lastUpdatedAt);
  const updateLabel = updated ? relativeTimeUk(updated) : 'очікується';

  const connLabel = useMemo(() => {
    if (connectionStatus === 'online') return 'Онлайн';
    if (connectionStatus === 'offline') return 'Офлайн';
    return 'Зʼєднання…';
  }, [connectionStatus]);

  const live = connectionStatus === 'online';

  return (
    <View style={styles.row}>
      <View style={styles.item}>
        <HeaderLiveIndicator active={live} size="sm" />
        <AppText variant="meta" muted>
          {connLabel}
        </AppText>
      </View>
      <AppText variant="meta" muted style={styles.dot}>
        ·
      </AppText>
      <AppText variant="meta" muted>
        {eventCount} активних
      </AppText>
      {highAttentionCount > 0 ? (
        <>
          <AppText variant="meta" muted style={styles.dot}>
            ·
          </AppText>
          <AppText variant="meta" style={{ color: theme.colors.warning }}>
            {highAttentionCount} увага
          </AppText>
        </>
      ) : null}
      <AppText variant="meta" muted style={styles.dot}>
        ·
      </AppText>
      <AppText variant="meta" muted numberOfLines={1} style={styles.flex}>
        {updateLabel}
        {onlineCount > 0 ? ` · ${onlineCount.toLocaleString('uk-UA')} онл.` : ''}
      </AppText>
    </View>
  );
}

function useSummaryStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        alignItems: 'center',
        paddingVertical: 6,
        gap: 4,
      },
      item: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
      },
      dot: {
        color: t.colors.textFaint,
      },
      flex: {
        flexShrink: 1,
      },
    }),
  );
}

export const RadarStatusSummary = memo(RadarStatusSummaryInner);

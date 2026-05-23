import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radarTheme } from '../constants/radarTheme';
import type { ConnectionStatus } from '../types/radar.types';
import { fonts } from '../../../theme/fonts';

const LABELS: Record<ConnectionStatus, string> = {
  live: 'Live',
  connecting: 'Зʼєднання…',
  offline: 'Офлайн',
  stale: 'Кеш',
};

const COLORS: Record<ConnectionStatus, string> = {
  live: radarTheme.live,
  connecting: radarTheme.warning,
  offline: radarTheme.textMuted,
  stale: radarTheme.warning,
};

type Props = { status: ConnectionStatus };

/** Static badge — no scale animation (avoids layout jitter in the feed header). */
export function RadarConnectionBadge({ status }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={[styles.dot, { backgroundColor: COLORS[status] }]} />
      <Text style={[styles.label, { color: COLORS[status] }]}>{LABELS[status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  label: { fontFamily: fonts.bold, fontSize: 11, letterSpacing: 0.3 },
});

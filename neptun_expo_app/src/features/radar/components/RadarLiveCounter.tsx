import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radarTheme } from '../constants/radarTheme';
import { fonts } from '../../../theme/fonts';

type Props = {
  eventCount: number;
  activeAlarms: number;
  lastFetchedLabel: string;
};

export function RadarLiveCounter({ eventCount, activeAlarms, lastFetchedLabel }: Props) {
  return (
    <View style={styles.row}>
      <View style={styles.stat}>
        <Text style={styles.value}>{eventCount}</Text>
        <Text style={styles.caption}>подій</Text>
      </View>
      <View style={styles.divider} />
      <View style={styles.stat}>
        <Text style={[styles.value, { color: radarTheme.danger }]}>{activeAlarms}</Text>
        <Text style={styles.caption}>тривог</Text>
      </View>
      <View style={styles.meta}>
        <Text style={styles.metaText}>оновлено {lastFetchedLabel}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 4,
  },
  stat: { alignItems: 'center', minWidth: 44 },
  value: { fontFamily: fonts.bold, fontSize: 18, color: radarTheme.text },
  caption: { fontFamily: fonts.medium, fontSize: 11, color: radarTheme.textMuted, marginTop: 2 },
  divider: { width: 1, height: 28, backgroundColor: radarTheme.border },
  meta: { flex: 1, alignItems: 'flex-end' },
  metaText: { fontFamily: fonts.medium, fontSize: 12, color: radarTheme.textMuted },
});

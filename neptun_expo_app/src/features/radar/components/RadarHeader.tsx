import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radarTheme } from '../constants/radarTheme';
import { fonts } from '../../../theme/fonts';
import { RadarConnectionBadge } from './RadarConnectionBadge';
import { RadarLiveCounter } from './RadarLiveCounter';
import type { ConnectionStatus } from '../types/radar.types';

type Props = {
  connectionStatus: ConnectionStatus;
  eventCount: number;
  activeAlarms: number;
  lastFetchedLabel: string;
};

/** Compact live status block below app chrome. */
export function RadarHeader({
  connectionStatus,
  eventCount,
  activeAlarms,
  lastFetchedLabel,
}: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.titleRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Радар загроз</Text>
          <Text style={styles.sub}>Моніторинг у реальному часі</Text>
        </View>
        <RadarConnectionBadge status={connectionStatus} />
      </View>
      <RadarLiveCounter
        eventCount={eventCount}
        activeAlarms={activeAlarms}
        lastFetchedLabel={lastFetchedLabel}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  titleRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  title: { fontFamily: fonts.bold, fontSize: 22, color: radarTheme.text, letterSpacing: -0.3 },
  sub: { fontFamily: fonts.medium, fontSize: 13, color: radarTheme.textMuted, marginTop: 2 },
});

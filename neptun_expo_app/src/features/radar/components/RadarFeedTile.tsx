import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import type { RadarFeedEntry } from '../logic/buildRadarFeed';
import {
  predictedEtaLabel,
  qualityPercent,
  threatTrackMetaFromMarker,
} from '../domain/threatTrackMeta';

function iconForType(typeKey: string): ComponentProps<typeof Ionicons>['name'] {
  switch (typeKey.toLowerCase()) {
    case 'raketa':
    case 'missile':
      return 'warning';
    case 'shahed':
    case 'drone':
      return 'radio';
    case 'avia':
      return 'airplane';
    default:
      return 'alert-circle';
  }
}

type Props = {
  entry: RadarFeedEntry;
  onPress?: (raw: Record<string, unknown>) => void;
};

/** Flutter `radar_feed_tile.dart` */
export function RadarFeedTile({ entry, onPress }: Props) {
  const { theme } = useAppTheme();
  const styles = useStyles();
  const meta = threatTrackMetaFromMarker(entry.raw);
  const eta = predictedEtaLabel(meta);
  const quality = qualityPercent(meta);

  return (
    <Pressable
      onPress={() => onPress?.(entry.raw)}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <Ionicons name={iconForType(entry.typeKey)} size={20} color={theme.colors.danger} />
      <View style={styles.body}>
        <Text style={styles.place} numberOfLines={2}>
          {entry.place}
        </Text>
        <Text muted style={styles.type} numberOfLines={1}>
          {entry.typeLabel}
        </Text>
        {(eta || quality != null) && (
          <View style={styles.badges}>
            {eta ? <Text style={styles.badge}>ETA {eta}</Text> : null}
            {quality != null ? <Text style={styles.badge}>Q {quality}%</Text> : null}
          </View>
        )}
      </View>
      <Text muted style={styles.time}>
        {entry.displayTime}
      </Text>
    </Pressable>
  );
}

function useStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 12,
        paddingVertical: 10,
        paddingHorizontal: 4,
      },
      pressed: { opacity: 0.85 },
      body: { flex: 1 },
      place: { fontFamily: fonts.semiBold, fontSize: 15, lineHeight: 20 },
      type: { marginTop: 4, fontSize: 13 },
      badges: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
      badge: {
        fontSize: 10,
        fontFamily: fonts.bold,
        color: t.colors.primary,
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 6,
        backgroundColor: t.colors.primarySoft,
        overflow: 'hidden',
      },
      time: { fontSize: 12, fontFamily: fonts.medium, marginTop: 2 },
    }),
  );
}

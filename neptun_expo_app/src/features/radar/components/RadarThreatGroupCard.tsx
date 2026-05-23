import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunSurface } from '../../../design/components/NeptunSurface';
import { palette, radii, spacing } from '../../../design/tokens';
import { radarThreatIconName } from '../domain/radarThreatIcon';
import { radarThreatTypeLabel } from '../domain/radarThreatLabel';
import {
  hasWaveBadge,
  predictedEtaLabel,
  qualityPercent,
  threatTrackMetaFromMarker,
} from '../domain/threatTrackMeta';
import { placesPreview } from '../logic/groupThreatMarkers';
import type { ThreatTypeGroup } from '../logic/groupThreatMarkers';
import { RadarStatusPill } from './RadarStatusPill';
import { fonts } from '../../../theme/fonts';

type Props = {
  group: ThreatTypeGroup;
};

type IonName = ComponentProps<typeof Ionicons>['name'];

function MetaChip({ label, icon }: { label: string; icon: IonName }) {
  return (
    <View style={styles.chip}>
      <Ionicons name={icon} size={12} color={palette.textMuted} />
      <Text style={styles.chipText}>{label}</Text>
    </View>
  );
}

/** Flutter `radar_tab.dart` grouped threat row. */
export function RadarThreatGroupCard({ group }: Props) {
  const meta = group.markers.length > 0 ? threatTrackMetaFromMarker(group.markers[0]) : null;
  const q = meta ? qualityPercent(meta) : undefined;
  const eta = meta ? predictedEtaLabel(meta) : undefined;

  return (
    <NeptunSurface variant="raised" padding={spacing.lg}>
      <View style={styles.row}>
        <View style={styles.iconBox}>
          <Ionicons name={radarThreatIconName(group.type)} size={20} color={palette.danger} />
        </View>
        <View style={styles.body}>
          <Text style={styles.title}>{radarThreatTypeLabel(group.type)}</Text>
          <Text muted style={styles.places} numberOfLines={1}>
            {placesPreview(group.markers)}
          </Text>
          {meta ? (
            <View style={styles.chips}>
              {q != null ? <MetaChip label={`${q}%`} icon="checkmark-circle-outline" /> : null}
              {hasWaveBadge(meta) ? <MetaChip label="хвиля" icon="layers-outline" /> : null}
              {meta.maneuverDetected ? <MetaChip label="маневр" icon="swap-horizontal" /> : null}
              {eta ? <MetaChip label={eta} icon="time-outline" /> : null}
            </View>
          ) : null}
        </View>
        <RadarStatusPill label={String(group.markers.length)} />
      </View>
    </NeptunSurface>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: radii.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.dangerMuted,
  },
  body: { flex: 1, minWidth: 0 },
  title: {
    fontFamily: fonts.semiBold,
    fontSize: 15,
    color: palette.text,
  },
  places: {
    marginTop: 2,
    fontSize: 12,
    lineHeight: 16,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 6,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: palette.surfaceHighlight,
  },
  chipText: {
    fontFamily: fonts.semiBold,
    fontSize: 11,
    color: palette.textSoft,
  },
});

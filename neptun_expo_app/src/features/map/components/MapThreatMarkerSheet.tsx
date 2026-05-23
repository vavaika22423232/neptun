import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { useRouter } from 'expo-router';
import { Pressable, Share, StyleSheet, View } from 'react-native';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { Text } from '../../../components/Text';
import type { ThreatMarker } from '../../../types/map';
import { radii, spacing } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { threatTypeColor, threatTypeNames } from '../constants/threatLabels';
import { parseThreatMarker } from '../utils/parseThreatMarker';
import { resolveThreatSheetStatus } from '../utils/threatSheetStatus';

type Props = {
  visible: boolean;
  raw: Record<string, unknown> | null;
  onClose: () => void;
};

/** Flutter `map_threat_marker_sheet.dart` + `threat_detail_sheet.dart` fields */
export function MapThreatMarkerSheet({ visible, raw, onClose }: Props) {
  const router = useRouter();
  const { theme } = useAppTheme();
  const c = theme.colors;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      headerRow: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
      iconBox: {
        width: 48,
        height: 48,
        borderRadius: radii.md,
        alignItems: 'center',
        justifyContent: 'center',
      },
      typeTitle: { fontFamily: fonts.semiBold, fontSize: 17, color: t.colors.textPrimary },
      place: { marginTop: 4, fontSize: 13, color: t.colors.textMuted },
      badge: {
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: radii.sm,
        borderWidth: StyleSheet.hairlineWidth,
      },
      badgeText: { fontFamily: fonts.bold, fontSize: 10, color: t.colors.textPrimary },
      textBox: {
        padding: spacing.lg,
        borderRadius: radii.lg,
        backgroundColor: t.colors.surfaceHighlight,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      textBody: { fontSize: 14, lineHeight: 21, color: t.colors.textSecondary },
      region: { fontFamily: fonts.semiBold, fontSize: 15, lineHeight: 20, color: t.colors.textSecondary },
      meta: { fontSize: 13, color: t.colors.textMuted },
      metaStrong: { fontFamily: fonts.semiBold, fontSize: 13, color: t.colors.textSecondary },
      hint: { fontSize: 12, lineHeight: 17, color: t.colors.textMuted },
      hintSmall: { fontSize: 11, lineHeight: 16, color: t.colors.textFaint },
      infoRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
      infoLabel: { fontSize: 13, color: t.colors.textMuted },
      infoValue: { flex: 1, fontFamily: fonts.medium, fontSize: 13, color: t.colors.textSecondary },
      row: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xs },
      outlineBtn: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        minHeight: 46,
        borderRadius: radii.md,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surfaceHighlight,
      },
      outlineLabel: { fontFamily: fonts.semiBold, fontSize: 14, color: t.colors.textPrimary },
    }),
  );

  if (!raw) return null;

  const marker = parseThreatMarker(raw) ?? fallbackMarker(raw);
  const typeLabel = threatTypeNames[marker.threatType] ?? marker.threatType;
  const status = resolveThreatSheetStatus(raw, marker);
  const hint = String(raw.display_trust_hint_uk ?? '').trim();
  const motionReason = String(raw.motion_reason ?? '').trim();

  let bearingLine: string | null = null;
  if (marker.courseBearing != null && Number.isFinite(marker.courseBearing)) {
    const dir = (marker.courseDirection ?? marker.arrowDirection ?? '').trim();
    bearingLine = dir ? `Курс ~${Math.round(marker.courseBearing)}° · ${dir}` : `Курс ~${Math.round(marker.courseBearing)}°`;
  }

  let trajSeg: string | null = null;
  let trajTarget: string | null = null;
  if (marker.trajectory) {
    const seg = `${marker.trajectory.sourceName} → ${marker.trajectory.targetName}`.trim();
    if (seg !== '→') trajSeg = seg;
    trajTarget = marker.trajectory.targetName || null;
  }
  const regionBlock = [marker.place, trajSeg].filter(Boolean).join('\n');

  let confidenceLine = '';
  if (marker.confidence0_100 != null) {
    confidenceLine = `Впевненість: ${marker.confidence0_100}%`;
    if (marker.placementMode) confidenceLine += ` · ${marker.placementMode}`;
  } else if (marker.placementMode) {
    confidenceLine = marker.placementMode;
  }

  const shareText = buildShareText(typeLabel, marker);
  const isUav = ['shahed', 'drone', 'uav', 'fpv'].includes(marker.threatType.toLowerCase());
  const typeColor = threatTypeColor(marker.threatType);

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.62}>
      <View style={styles.headerRow}>
        <View style={[styles.iconBox, { backgroundColor: typeColor + '22' }]}>
          <Ionicons name={threatIcon(marker.threatType)} size={22} color={typeColor} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.typeTitle}>{typeLabel}</Text>
          {marker.place ? <Text style={styles.place}>{marker.place}</Text> : null}
        </View>
        <View style={[styles.badge, { borderColor: status.color + '55', backgroundColor: status.color + '22' }]}>
          <Text style={styles.badgeText}>{status.label}</Text>
        </View>
      </View>

      {marker.text ? (
        <View style={styles.textBox}>
          <Text style={styles.textBody}>{marker.text}</Text>
        </View>
      ) : null}

      {regionBlock ? <Text style={styles.region}>{regionBlock}</Text> : null}
      {marker.date ? <Text style={styles.meta}>Час: {marker.date}</Text> : null}
      {bearingLine ? <Text style={styles.metaStrong}>{bearingLine}</Text> : null}
      {confidenceLine ? <Text style={styles.meta}>{confidenceLine}</Text> : null}
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      {motionReason ? <Text style={styles.hintSmall}>{motionReason}</Text> : null}

      {isUav && marker.count != null && marker.count > 1 ? (
        <InfoRow styles={styles} icon="grid-outline" label="Кількість" value={`×${marker.count}`} muted={c.textMuted} />
      ) : null}
      {trajTarget ? (
        <InfoRow styles={styles} icon="navigate-outline" label="Напрямок" value={trajTarget} muted={c.textMuted} />
      ) : null}
      <InfoRow
        styles={styles}
        icon="locate-outline"
        label="Координати"
        value={`${marker.lat.toFixed(4)}, ${marker.lng.toFixed(4)}`}
        muted={c.textMuted}
      />

      <View style={styles.row}>
        <Pressable
          style={styles.outlineBtn}
          onPress={() => {
            onClose();
            router.push('/(tabs)/radar');
          }}
        >
          <Ionicons name="radio-outline" size={18} color={c.textPrimary} />
          <Text style={styles.outlineLabel}>Відкрити радар</Text>
        </Pressable>
        <Pressable
          style={styles.outlineBtn}
          onPress={() => {
            onClose();
            router.push('/(tabs)/regions');
          }}
        >
          <Ionicons name="notifications-outline" size={18} color={c.textPrimary} />
          <Text style={styles.outlineLabel}>Сповіщення</Text>
        </Pressable>
      </View>

      <PrimaryButton onPress={() => void Share.share({ message: shareText })}>Поділитись</PrimaryButton>
    </NeptunBottomSheet>
  );
}

function InfoRow({
  icon,
  label,
  value,
  styles,
  muted,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
  styles: { infoRow: object; infoLabel: object; infoValue: object };
  muted: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon} size={16} color={muted} />
      <Text style={styles.infoLabel}>{label}: </Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function threatIcon(type: string): ComponentProps<typeof Ionicons>['name'] {
  switch (type.toLowerCase()) {
    case 'shahed':
    case 'drone':
      return 'airplane';
    case 'raketa':
    case 'missile':
      return 'rocket-outline';
    case 'avia':
      return 'airplane-outline';
    default:
      return 'alert-circle';
  }
}

function fallbackMarker(raw: Record<string, unknown>): ThreatMarker {
  return {
    lat: Number(raw.lat) || 0,
    lng: Number(raw.lng) || 0,
    threatType: String(raw.threat_type ?? 'default'),
    place: String(raw.place ?? ''),
    text: String(raw.text ?? ''),
    date: String(raw.date ?? ''),
    updatedAt: Date.now(),
  };
}

function buildShareText(typeLabel: string, m: ThreatMarker): string {
  const lines = [typeLabel];
  if (m.place) lines.push(m.place);
  if (m.date) lines.push(m.date);
  lines.push('', 'NEPTUN — https://neptun.in.ua');
  return lines.join('\n');
}

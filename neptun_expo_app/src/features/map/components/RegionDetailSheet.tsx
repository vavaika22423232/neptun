import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { Text } from '../../../components/Text';
import { palette, radii, spacing } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  visible: boolean;
  regionName: string;
  isAlarmActive?: boolean;
  alarmStartTime?: number | null;
  threatCount?: number;
  onClose: () => void;
};

export function RegionDetailSheet({
  visible,
  regionName,
  isAlarmActive = false,
  alarmStartTime,
  threatCount = 0,
  onClose,
}: Props) {
  const durationLabel = formatAlarmDuration(alarmStartTime);

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.4} scrollable={false}>
      <View style={styles.headerRow}>
        <View
          style={[
            styles.iconBox,
            { backgroundColor: isAlarmActive ? palette.dangerMuted : palette.successMuted },
          ]}
        >
          <Ionicons
            name={isAlarmActive ? 'warning-outline' : 'checkmark-circle-outline'}
            size={22}
            color={isAlarmActive ? palette.danger : palette.success}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{regionName}</Text>
          <Text style={[styles.sub, { color: isAlarmActive ? palette.danger : palette.success }]}>
            {isAlarmActive ? 'Повітряна тривога' : 'Відбій'}
          </Text>
        </View>
        <View style={[styles.badge, isAlarmActive ? styles.badgeDanger : styles.badgeOk]}>
          <Text style={styles.badgeText}>{isAlarmActive ? 'Тривога' : 'Спокійно'}</Text>
        </View>
      </View>

      <View style={styles.statsRow}>
        <StatCard icon="alert-circle-outline" label="Загрози" value={String(threatCount)} />
        {durationLabel ? <StatCard icon="time-outline" label="Тривалість" value={durationLabel} /> : null}
      </View>
    </NeptunBottomSheet>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
}) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon} size={16} color={palette.accentSoft} />
      <Text style={styles.statValue}>{value}</Text>
      <Text muted style={styles.statLabel}>
        {label}
      </Text>
    </View>
  );
}

function formatAlarmDuration(startMs?: number | null): string | null {
  if (startMs == null || !Number.isFinite(startMs)) return null;
  const d = Date.now() - startMs;
  if (d < 0) return null;
  const hours = Math.floor(d / 3600000);
  const mins = Math.floor((d % 3600000) / 60000);
  if (hours > 0) return `${hours}г ${mins}хв`;
  return `${mins}хв`;
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  iconBox: {
    width: 48,
    height: 48,
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: { fontFamily: fonts.semiBold, fontSize: 17, color: palette.text },
  sub: { marginTop: 4, fontSize: 13, fontFamily: fonts.medium },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
  },
  badgeDanger: { borderColor: palette.danger + '55', backgroundColor: palette.dangerMuted },
  badgeOk: { borderColor: palette.success + '44', backgroundColor: palette.successMuted },
  badgeText: { fontFamily: fonts.semiBold, fontSize: 11, color: palette.textSoft },
  statsRow: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.md },
  statCard: {
    flex: 1,
    padding: spacing.lg,
    borderRadius: radii.lg,
    backgroundColor: palette.surfaceHighlight,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.border,
    gap: 6,
  },
  statValue: { fontFamily: fonts.bold, fontSize: 20, color: palette.text },
  statLabel: { fontSize: 12 },
});

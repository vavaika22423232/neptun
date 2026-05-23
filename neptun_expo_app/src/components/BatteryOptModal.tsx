import { Ionicons } from '@expo/vector-icons';
import { Modal, StyleSheet, View } from 'react-native';
import { palette, radii, spacing } from '../design/tokens';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { fonts } from '../theme/fonts';
import { Text } from './Text';

type Props = {
  visible: boolean;
  onLater: () => void;
  onOpenSettings: () => void;
};

export function BatteryOptModal({ visible, onLater, onOpenSettings }: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onLater}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <View style={styles.titleRow}>
            <View style={styles.iconWrap}>
              <Ionicons name="battery-charging-outline" size={24} color={palette.warning} />
            </View>
            <Text style={styles.title}>Надійні сповіщення</Text>
          </View>
          <Text muted style={styles.body}>
            Оптимізація батареї може затримувати критичні сповіщення.{'\n\n'}
            Вимкніть її для Neptun, щоб отримувати попередження вчасно.
          </Text>
          <View style={styles.actions}>
            <NeptunPressable haptic={false} onPress={onLater} style={styles.laterBtn}>
              <Text style={styles.laterText}>Пізніше</Text>
            </NeptunPressable>
            <NeptunPressable haptic onPress={onOpenSettings} style={styles.primaryBtn}>
              <Text style={styles.primaryText}>Відкрити налаштування</Text>
            </NeptunPressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: palette.overlay,
    justifyContent: 'center',
    padding: spacing.xxxl,
  },
  card: {
    backgroundColor: palette.surfaceGlassStrong,
    borderRadius: radii.xl,
    padding: spacing.xl,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  iconWrap: {
    padding: spacing.sm,
    borderRadius: radii.md,
    backgroundColor: palette.warningMuted,
  },
  title: {
    flex: 1,
    fontFamily: fonts.bold,
    fontSize: 18,
    color: palette.text,
  },
  body: { fontSize: 14, lineHeight: 21, marginBottom: spacing.xl },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.md,
    alignItems: 'center',
  },
  laterBtn: { paddingVertical: 10, paddingHorizontal: 12 },
  laterText: { fontFamily: fonts.semiBold, fontSize: 15, color: palette.textMuted },
  primaryBtn: {
    backgroundColor: palette.accent,
    paddingVertical: 11,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
  },
  primaryText: { fontFamily: fonts.bold, fontSize: 15, color: '#041018' },
});

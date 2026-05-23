import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { palette, spacing, typography } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  onDismiss: () => void;
};

export function RadarTelegramInlineRow({ onDismiss }: Props) {
  return (
    <View style={styles.root}>
      <NeptunPressable
        haptic={false}
        style={styles.link}
        onPress={() => void openNeptunTelegramChannel('radar_banner')}
        accessibilityRole="link"
      >
        <Ionicons name="paper-plane-outline" size={18} color={palette.accentSoft} />
        <Text style={styles.linkText} numberOfLines={2}>
          Канал у Telegram — швидкі оновлення
        </Text>
      </NeptunPressable>
      <NeptunPressable haptic={false} onPress={onDismiss} hitSlop={10} accessibilityLabel="Приховати">
        <Ionicons name="close" size={20} color={palette.textMuted} />
      </NeptunPressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: palette.border,
    marginBottom: spacing.sm,
  },
  link: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingBottom: spacing.sm,
  },
  linkText: {
    flex: 1,
    fontFamily: fonts.semiBold,
    ...typography.callout,
    color: palette.textSoft,
  },
});

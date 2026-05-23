import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { useEffectiveOnline } from '../core/connectivity/useEffectiveOnline';
import { radii, spacing, typography } from '../design/tokens';
import { fonts } from '../theme/fonts';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';
import { Text } from './Text';

export function OfflineBanner() {
  const state = useEffectiveOnline();
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        backgroundColor: t.colors.warningMuted,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.border,
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.md,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
      },
      iconBox: {
        padding: spacing.sm,
        borderRadius: radii.md,
        backgroundColor: t.colors.warning + '1F',
      },
      copy: { flex: 1, gap: 2 },
      title: {
        fontFamily: fonts.semiBold,
        ...typography.callout,
        color: t.colors.warning,
      },
      subtitle: { ...typography.caption, color: t.colors.textSecondary },
    }),
  );

  if (state === 'online') return null;

  const isApiDown = state === 'apiUnreachable';
  const title = isApiDown ? 'Сервер недоступний' : "Немає з'єднання";
  const subtitle = isApiDown
    ? "Перевіряємо зв'язок із сервером"
    : 'Перевірте Wi‑Fi або мобільні дані';
  const icon = isApiDown ? 'cloud-offline-outline' : 'wifi-outline';

  return (
    <Animated.View entering={FadeIn.duration(280)} exiting={FadeOut.duration(220)} style={styles.wrap}>
      <View style={styles.row}>
        <View style={styles.iconBox}>
          <Ionicons name={icon} size={20} color={theme.colors.warning} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
      </View>
    </Animated.View>
  );
}

import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { spacing } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

import { mapTabHeaderBottom } from './MapTabHeader';

type Props = {
  onDismiss: () => void;
};

export function BallisticThreatOverlay({ onDismiss }: Props) {
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const c = theme.colors;

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        position: 'absolute',
        left: spacing.md,
        right: spacing.md,
        zIndex: 30,
        elevation: 4,
        alignItems: 'center',
      },
      card: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
        paddingHorizontal: spacing.md,
        paddingVertical: 10,
        borderRadius: 8,
        backgroundColor: t.colors.surface,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.danger + '44',
      },
      iconWrap: {
        width: 28,
        height: 28,
        borderRadius: 6,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.dangerMuted,
      },
      body: { flex: 1, minWidth: 0 },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        lineHeight: 18,
        color: t.colors.danger,
      },
      sub: {
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
        color: t.colors.textSecondary,
      },
    }),
  );

  return (
    <View
      style={[styles.wrap, { top: mapTabHeaderBottom(insets.top) }]}
      pointerEvents="box-none"
    >
      <NeptunPressable haptic onPress={onDismiss} style={styles.card}>
        <View style={styles.iconWrap}>
          <Ionicons name="warning-outline" size={16} color={c.danger} />
        </View>
        <View style={styles.body}>
          <Text style={styles.title}>Загроза балістики</Text>
          <Text style={styles.sub} numberOfLines={1}>
            Негайно прямуйте в укриття
          </Text>
        </View>
        <Ionicons name="close" size={18} color={c.textMuted} />
      </NeptunPressable>
    </View>
  );
}

import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { spacing } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

import { mapTabHeaderBottom } from './MapTabHeader';

type Props = {
  progress: number;
  message?: string;
};

export function BallisticAllClearOverlay({ progress, message }: Props) {
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const c = theme.colors;

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        position: 'absolute',
        left: spacing.md,
        right: spacing.md,
        zIndex: 29,
        elevation: 4,
        alignItems: 'stretch',
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
        borderColor: t.colors.success + '44',
      },
      iconWrap: {
        width: 28,
        height: 28,
        borderRadius: 6,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.successMuted,
      },
      body: { flex: 1, minWidth: 0 },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        lineHeight: 18,
        color: t.colors.success,
      },
      sub: {
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
        color: t.colors.textSecondary,
      },
      track: {
        width: 48,
        height: 3,
        borderRadius: 2,
        backgroundColor: t.colors.divider,
        overflow: 'hidden',
      },
      fill: {
        height: 3,
        borderRadius: 2,
        backgroundColor: t.colors.success,
      },
    }),
  );

  if (progress >= 1) return null;
  const opacity = progress < 0.7 ? 1 : Math.max(0, 1 - (progress - 0.7) * 3.3);

  return (
    <View
      style={[
        styles.wrap,
        { top: mapTabHeaderBottom(insets.top), opacity },
      ]}
      pointerEvents="none"
    >
      <View style={styles.card}>
        <View style={styles.iconWrap}>
          <Ionicons name="checkmark-circle-outline" size={16} color={c.success} />
        </View>
        <View style={styles.body}>
          <Text style={styles.title} numberOfLines={1}>
            Відбій
          </Text>
          {message ? (
            <Text style={styles.sub} numberOfLines={1}>
              {message}
            </Text>
          ) : null}
        </View>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${Math.round(progress * 100)}%` }]} />
        </View>
      </View>
    </View>
  );
}

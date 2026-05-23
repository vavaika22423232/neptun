import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { PrimaryButton } from '../../components/PrimaryButton';
import { Text } from '../../components/Text';
import { fonts } from '../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { radii, spacing } from '../tokens';

type Props = {
  icon?: ComponentProps<typeof Ionicons>['name'];
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function NeptunEmptyState({ icon = 'sparkles-outline', title, subtitle, actionLabel, onAction }: Props) {
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        alignItems: 'center',
        paddingVertical: spacing.xxxl,
        paddingHorizontal: spacing.xl,
        gap: spacing.sm,
      },
      iconWrap: {
        width: 56,
        height: 56,
        borderRadius: radii.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primaryMuted,
        marginBottom: spacing.sm,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 16,
        textAlign: 'center',
        color: t.colors.textPrimary,
      },
      subtitle: {
        textAlign: 'center',
        fontSize: 13,
        lineHeight: 18,
        color: t.colors.textMuted,
      },
      cta: { marginTop: spacing.lg, width: '100%', maxWidth: 280 },
    }),
  );

  return (
    <View style={styles.root}>
      <View style={styles.iconWrap}>
        <Ionicons name={icon} size={28} color={theme.colors.primary} />
      </View>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      {actionLabel && onAction ? (
        <View style={styles.cta}>
          <PrimaryButton onPress={onAction}>{actionLabel}</PrimaryButton>
        </View>
      ) : null}
    </View>
  );
}

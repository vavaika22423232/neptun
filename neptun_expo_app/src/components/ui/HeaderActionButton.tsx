import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';
import { Text } from '../Text';

export type HeaderActionTone = 'default' | 'telegram' | 'warning' | 'premium';

type Props = {
  icon: ComponentProps<typeof Ionicons>['name'];
  onPress?: () => void;
  tone?: HeaderActionTone;
  label?: string;
  accessibilityLabel?: string;
  /** Slightly smaller pill for dense map overlay. */
  compact?: boolean;
};

export const HeaderActionButton = memo(function HeaderActionButton({
  icon,
  onPress,
  tone = 'default',
  label,
  accessibilityLabel,
  compact = false,
}: Props) {
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      iconBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surfaceHighlight,
      },
      proPill: {
        height: 44,
        paddingHorizontal: 12,
        borderRadius: 22,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
        backgroundColor: t.colors.proSoft,
      },
      proPillCompact: {
        height: 40,
        paddingHorizontal: 10,
        borderRadius: 20,
      },
      proLabel: {
        fontFamily: fonts.bold,
        fontSize: 13,
        letterSpacing: 0.3,
        color: t.colors.premiumDeep,
      },
      proLabelCompact: {
        fontSize: 12,
      },
    }),
  );

  const iconColor =
    tone === 'telegram'
      ? theme.colors.primary
      : tone === 'warning'
        ? theme.colors.warning
        : tone === 'premium'
          ? theme.colors.pro
          : theme.colors.textSecondary;

  if (label) {
    return (
      <NeptunPressable
        haptic
        scaleTo={0.94}
        accessibilityLabel={accessibilityLabel ?? label}
        onPress={onPress}
        style={[styles.proPill, compact && styles.proPillCompact]}
      >
        <Ionicons name={icon} size={17} color={iconColor} />
        <Text style={[styles.proLabel, compact && styles.proLabelCompact]}>{label}</Text>
      </NeptunPressable>
    );
  }

  return (
    <NeptunPressable
      haptic
      scaleTo={0.94}
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      style={styles.iconBtn}
    >
      <Ionicons name={icon} size={20} color={iconColor} />
    </NeptunPressable>
  );
});

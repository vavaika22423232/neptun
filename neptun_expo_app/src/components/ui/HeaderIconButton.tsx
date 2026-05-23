import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';

export type HeaderIconTone = 'default' | 'accent' | 'warning' | 'premium';

type Props = {
  icon: ComponentProps<typeof Ionicons>['name'];
  onPress?: () => void;
  tone?: HeaderIconTone;
  size?: number;
  accessibilityLabel?: string;
};

export const HeaderIconButton = memo(function HeaderIconButton({
  icon,
  onPress,
  tone = 'default',
  size = 40,
  accessibilityLabel,
}: Props) {
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      btn: {
        width: size,
        height: size,
        borderRadius: size / 2,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surfaceHighlight,
      },
    }),
  );

  const color =
    tone === 'accent'
      ? theme.colors.primary
      : tone === 'warning'
        ? theme.colors.warning
        : tone === 'premium'
          ? theme.colors.pro
          : theme.colors.textSecondary;

  return (
    <NeptunPressable
      haptic
      scaleTo={0.94}
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      style={styles.btn}
    >
      <Ionicons name={icon} size={20} color={color} />
    </NeptunPressable>
  );
});

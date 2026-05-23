import { StyleSheet } from 'react-native';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { useThemedStyles } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';
import { Text } from './Text';

type Props = {
  children: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
};

export function PrimaryButton({ children, onPress, disabled, variant = 'primary' }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        minHeight: 52,
        borderRadius: t.radii.md,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primary,
        paddingHorizontal: 20,
      },
      secondary: {
        backgroundColor: t.colors.surfaceHighlight,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
      },
      ghost: {
        backgroundColor: 'transparent',
      },
      disabled: { opacity: 0.5 },
      label: {
        color: t.colors.onAccent,
        fontFamily: fonts.bold,
        fontSize: t.typography.title3.fontSize,
      },
      labelSecondary: { color: t.colors.textPrimary },
      labelGhost: { color: t.colors.primary },
    }),
  );

  return (
    <NeptunPressable
      disabled={disabled}
      onPress={onPress}
      haptic={!disabled}
      style={[
        styles.root,
        variant === 'secondary' && styles.secondary,
        variant === 'ghost' && styles.ghost,
        disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          styles.label,
          variant === 'secondary' && styles.labelSecondary,
          variant === 'ghost' && styles.labelGhost,
        ]}
      >
        {children}
      </Text>
    </NeptunPressable>
  );
}

import { Pressable, StyleSheet, View, type ViewProps } from 'react-native';
import { radii, spacing } from '../tokens';
import { useThemedStyles } from '../../theme/useAppTheme';

type Variant = 'flat' | 'raised';

type Props = ViewProps & {
  variant?: Variant;
  onPress?: () => void;
  padding?: number;
  radius?: number;
};

/** Flat surface card — no glass, no gradients. */
export function NeptunSurface({
  variant = 'flat',
  onPress,
  padding = 0,
  radius = radii.lg,
  style,
  children,
  ...rest
}: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      base: {
        backgroundColor: variant === 'raised' ? t.colors.surfaceElevated : t.colors.card,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        overflow: 'hidden',
        marginBottom: spacing.md,
      },
      pressed: { opacity: 0.94 },
    }),
  );

  const shell = (
    <View {...rest} style={[styles.base, { borderRadius: radius, padding }, style]}>
      {children}
    </View>
  );

  if (!onPress) return shell;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [pressed && styles.pressed]}>
      {shell}
    </Pressable>
  );
}

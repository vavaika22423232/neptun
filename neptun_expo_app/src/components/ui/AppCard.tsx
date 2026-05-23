import type { ViewProps } from 'react-native';
import { StyleSheet, View } from 'react-native';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useThemedStyles } from '../../theme/useAppTheme';

type Props = ViewProps & {
  elevated?: boolean;
  onPress?: () => void;
};

export function AppCard({ style, elevated, onPress, children, ...props }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        borderRadius: t.radii.lg,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: elevated ? t.colors.borderStrong : t.colors.border,
        backgroundColor: elevated ? t.colors.cardElevated : t.colors.card,
        padding: t.spacing.lg,
      },
    }),
  );

  if (onPress) {
    return (
      <NeptunPressable haptic scaleTo={0.99} onPress={onPress} style={[styles.card, style]}>
        {children}
      </NeptunPressable>
    );
  }

  return (
    <View {...props} style={[styles.card, style]}>
      {children}
    </View>
  );
}

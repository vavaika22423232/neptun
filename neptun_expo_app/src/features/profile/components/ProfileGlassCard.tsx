import type { ReactNode } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  children: ReactNode;
  padding?: number;
  style?: ViewStyle;
  elevated?: boolean;
};

export function ProfileGlassCard({ children, padding = 16, style, elevated }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        borderRadius: t.radii.xl,
        backgroundColor: t.colors.card,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        overflow: 'hidden',
        ...t.shadows.sm,
      },
      elevated: {
        backgroundColor: t.colors.cardElevated,
        ...t.shadows.md,
      },
      highlight: {
        position: 'absolute',
        top: 0,
        left: 20,
        right: 20,
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.scheme === 'light' ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.06)',
      },
    }),
  );

  return (
    <View style={[styles.card, elevated && styles.elevated, { padding }, style]}>
      <View style={styles.highlight} pointerEvents="none" />
      {children}
    </View>
  );
}
